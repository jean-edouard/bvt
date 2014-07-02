#
# Copyright (c) 2013 Citrix Systems, Inc.
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

"""Launch subprocesses"""

from subprocess import Popen, PIPE
from os import kill, read, close
from time import time
from pipes import quote
from signal import SIGKILL
from tempfile import mkstemp, mkdtemp
from os import unlink
from bvtlib.time_limit import time_limit, TimeoutError
from select import POLLIN, POLLPRI, poll, error
from errno import EINTR
from bvtlib.settings import TEST_MACHINE_DOMAIN_POSTFIX
from os.path import exists
from bvtlib.retry import retry

class SubprocessError(Exception):
    """A subprocess failed"""

class SubprocessFailure(SubprocessError):
    """A subprocess returned a non-zero exit code"""

class UnableToRunCommandsOnHost(SubprocessError):
    """Unable to run commands on host"""

class ScpViaRootNeedsAbsolutePath(Exception):
    """SCP via root needs an absolute filename.
This is because relative names are based on the user's home
directory, but we can't resolve that efficiently."""

def space_escape(args):
    """Escale spaces in args"""
    return [quote(x) for x in args]

def run(args, timeout=60, host=None, split=False, word_split=False, 
        line_split=False,
        ignore_failure=False, verify=True,
        cwd=None, user=None, env={}, shell=False, stderr=False,  echo=False, 
        verbose=True, announce_interval = 20, wait=True,
        stdin_push='', output_callback=None, 
        error_callback=None, check_host_key=True):
    """Run command with args, or raise SubprocessTimeout after timeout seconds.

    If host is specified, ssh to that machine. Let's hope your ssh configuration
    works.

    If split is true, convert output to a list of lines, where each
    line is a list of words.
    
    If word_split is true, convert output to a list of whitespace separated words.

    If line_split is true, convert output to a list of lines.

    If ignore_failure is true, do not raise exceptions for non-zero exit codes.
    
    If cwd is true, run commands in that working directory using a shell.

    If env is a dictionary, set those environment variables.

    If shell is true, run through a shell (implied by cwd or env).

    If stderr is true, return stderr as well as stdout. Otherwise or by default
    return just stdout.

    If echo is true, echo stdout/stderr through to sys.stdout/sys.stderr

    If verbose is true, print arguments timing and exit code.
    See http://stackoverflow.com/questions/1191374/subprocess-with-timeout

    If verify and host are set, then make sure the connection to the host
    works before trying it.

    If wait is false, then simply launch the command and return straight away.
    """
    description = ' '.join(args)
    if host and verify:
        verify_connection(host, user, timeout=timeout, check_host_key=check_host_key)
    
    spargs = space_escape(args)    
    if host:
        shell_prefixes = []
        if cwd:
            shell_prefixes.extend(['cd', cwd, '&&'])
            cwd = None
        for key, value in env.iteritems():
            shell_prefixes.append("%s=%s" % (key, (space_escape([value])[0])))
        env = None
        if '.' not in host: 
            host += TEST_MACHINE_DOMAIN_POSTFIX
        shell = False
        args = ['ssh', '-oPasswordAuthentication=no', '-l' + (user if user else 'root'), host]
        if not check_host_key:
            args.extend(['-oStrictHostKeyChecking=no', '-oUserKnownHostsFile=/dev/null'])
        args += shell_prefixes + spargs
        description += ' on '+host
    if verbose:
        print 'RUN:', repr(args)
    process = Popen(args, stdout=PIPE, stderr=PIPE, stdin=PIPE, shell=shell,
                    env=env, cwd=cwd)

    fd2output = {}
    fd2file = {}
    poller = poll()

    def register_and_append(file_obj, eventmask):
        """Record file_obj for poll operations"""
        poller.register(file_obj.fileno(), eventmask)
        fd2file[file_obj.fileno()] = file_obj
        out = fd2output[file_obj.fileno()] = []
        return out
    def close_unregister_and_remove(fdes):
        """fdes is finished"""
        poller.unregister(fdes)
        fd2file[fdes].close()
        fd2file.pop(fdes)


    stdout_list = register_and_append(process.stdout, POLLIN | POLLPRI)
    stderr_list = register_and_append(process.stderr, POLLIN | POLLPRI)

    def throw_timeout(delay):
        """Throw exception for after delay"""
        try:
            out = run(['ps', '--no-headers', '-o', 'pid', '--ppid', 
                       str(process.pid)])
        except SubprocessError:
            out = ''
        pids = [process.pid] + [int(p) for p in out.split()]
        for pid in pids:
            try:
                kill(pid, SIGKILL)
            except OSError:
                print 'WARNING: unable to kill subprocess', pid
        raise TimeoutError(description, timeout, delay,
                           ''.join(stdout_list),
                           ''.join(stderr_list))

    if not wait:
        return

    start = time()
    with time_limit(timeout, 'launch '+' '.join(args), 
                    timeout_callback=throw_timeout):
        if stdin_push:
            process.stdin.write(stdin_push)
            process.stdin.flush()
            process.stdin.close()
        announce = time() + announce_interval
        while fd2file:
            if time() > announce:
                announce = time() + announce_interval
                print 'NOTE: waiting', time() - start, 'of', timeout, \
                    'seconds for', ' '.join(args)
            try:
                ready = poller.poll(20)
            except error, eparam:
                if eparam.args[0] == EINTR:
                    continue
                raise
            for fdes, mode in ready:
                if not mode & (POLLIN | POLLPRI):
                    close_unregister_and_remove(fdes)
                    continue
                if fdes not in fd2file:
                    print 'operation on unexpected FD', fdes
                    continue
                data = read(fdes, 4096)
                if not data:
                    close_unregister_and_remove(fdes)
                fd2output[fdes].append(data)
                fileobj = fd2file[fdes]
                if fileobj == process.stdout:
                    if echo:
                        for line in data.splitlines():
                            print 'STDOUT:', line
                    if output_callback:
                        output_callback(data)
                if fileobj == process.stderr:
                    if echo:
                        for line in data.splitlines():
                            print 'STDERR:', line
                    if error_callback:
                        error_callback(data)
            
        process.wait()
        output = ''.join(stdout_list), ''.join(stderr_list)
        exit_code = process.returncode

    delay = time() - start
    
    if verbose:
        print 'RUN: finished', ' '.join(args), 'rc', exit_code, \
            'in', delay, 'seconds', \
            'output', len(output[0]), 'characters'
    if exit_code != 0 and not ignore_failure:
        raise SubprocessError(description, exit_code, output[0], output[1])
    if word_split:
        outv = [x.split() for x in output]
        assert not split # specifiy one of split and word_split only
    elif split:
        outv = [[line.split() for line in x.split('\n')] for 
            x in output] 
    elif line_split:
        outv = [x.split('\n') for x in output]
    else:
        outv = output
    if stderr:
        return (outv[0], outv[1], exit_code) if ignore_failure else outv
    else:
        return (outv[0], exit_code) if ignore_failure else outv[0]

def statcheck(filename, predicate, **args):
    """Return output of predicate or split up stat output on filename,
    or False if stat fails. Supports arguments of run()"""
    if args.get('host'):
        verify_connection(args['host'], args.get('user', 'root'), timeout=10)
    statout, exitcode = run(['stat', filename], split=True, ignore_failure=True,
                      **args)
    if statout == [[]] or exitcode != 0:
        return False
    result = predicate(statout)
    return result
        
def isfile(filename, **args):
    """Is filename a file? Supports arguments of run()"""
    return statcheck(filename, lambda x: x[1][-1] == 'file', **args)
    

def isdir(filename, **args):
    """Is filename a directory? Supports arguments of run()"""
    return statcheck(filename, lambda x: x[1][-1] == 'directory', **args)

def islink(filename, **args):
    """Is filename a symbolic link? Supports arguments of run()"""
    return statcheck(filename, lambda x: x[1][-2:] == ['symbolic', 'link'], 
                     **args)

def readfile(filename, host=None, user='root', **args):
    """Return contents of filename on host"""
    if host == None:
        return file(filename, 'rb').read()
    handle, temp = mkstemp()
    try:
        verify_connection(host, user, timeout=10)
        if '.' not in host:
            host += TEST_MACHINE_DOMAIN_POSTFIX
        run(['scp', user+'@'+host+':'+filename, temp], env=None, **args)
        return file(temp, 'rb').read()
    finally:
        unlink(temp)
        close(handle)

def writefile(filename, content, host=None, user='root', via_root=False,
              **args):
    """Write contents at filename on host"""
    if host == None:
        temp = filename
    else:
        if via_root and not filename.startswith('/'):
            raise ScpViaRootNeedsAbsolutePath(filename)
        if '.' not in host:
            host += TEST_MACHINE_DOMAIN_POSTFIX
        fd, temp = mkstemp()
        close(fd)
    fobj = file(temp, 'wb')
    fobj.write(content)
    fobj.close()
    if host == None:
        return
    try:
        if via_root:
            run(['scp', temp, 'root@'+host+':'+filename], env=None,
                **args)
            run(['chown', user, filename], user='root', host=host)
        else:
            run(['scp', temp, user+'@'+host+':'+filename], env=None,
                **args)
    finally:
        unlink(temp)
    run(['chmod', 'a+rx', filename], host=host, **args)
        
def specify(**options):
    """Return a version of run with options set"""
    def subrun(args, **loptions):
        """Run args with options"""
        for key, value in options.items():
            loptions.setdefault(key, value)
        return run(args, **loptions)
    return subrun


def verify_connection(host, user, timeout=60, check_host_key=True):
    """Verify that we can connect to host as user"""
    def go():
        run(['true'], verify=False, host=host, user=user, timeout=5, check_host_key=check_host_key)
    try:
        retry(go, 'run true on '+host, timeout=timeout)
    except Exception,exc:
        print 'RUN: first stage verify failed with', exc
    else:
        return
    
    for line in run(['ps', 'uaxxwww'], split=True):
        if 'ssh' in line and host in line:
            print 'RUN: killing ssh process', line
            try:
                kill(int(line[1]), SIGKILL)
            except OSError:
                print 'NOTE: unable to kill', line[1]
        sfile = '/tmp/root@'+host+':22'
        if exists(sfile):
            try:
                unlink(sfile)
            except OSError:
                pass
    try:
        go()
    except Exception, exc:
        print 'RUN: second stage verify failed with', repr(exc)
        raise UnableToRunCommandsOnHost(host, user, exc)

def maketempfile(host=None, postfix=''):
    """Make temporary file on host"""
    return run(['mktemp', '/tmp/tmpXXXXXXXXXX' + postfix],
               host=host).rstrip('\n')

def maketempdirectory(host=None, postfix=''):
    """Make temporary file on host"""
    return run(['mktemp', '-d', '/tmp/tmpXXXXXXXXXX' + postfix],
               host=host).rstrip('\n')
