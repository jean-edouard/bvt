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

"""Call exec daemon (see ../execdaemon)"""
from xmlrpclib import ServerProxy, Fault
from src.bvtlib.time_limit import time_limit
from src.bvtlib.settings import EXEC_DAEMON_URL_FORMAT
from time import sleep
from socket import error
from src.bvtlib.retry import retry

class SubprocessError(Exception):
    """A subprocess failed"""

# TODO: make host not optional
def call_exec_daemon(command, args=list(), host=None, timeout=60, why=''):
    """Invoke the exec daemon with args on host.

    (Use domain_address to get a suitable host parameter
    """
    assert host is not None
    def inner():
        with time_limit(timeout, 
                        'call %s%r on %s %s' % (command, args, host, why)):
            print 'RUN: calling', command, 'arguments', args, 'on', host
            proxy = ServerProxy(EXEC_DAEMON_URL_FORMAT % (host))
            return getattr(proxy, command)(*args)
    return retry(inner, 'call exec daemon  on '+repr(host)+' '+why, timeout=timeout,
          catch=[error])

def run_via_exec_daemon(args, host, timeout=60, ignore_failure=False,
                        split=False, word_split=False,line_split=False, echo=True, wait=True):
    """Run args on host.

    Fail after timeout.

    Unless ignore_failure is True, if the command fails raise SubprocessFailure.

    If split is set, split up to list of words per line.

    Intended to be similar to src.bvtlib.run.run"""
    process = call_exec_daemon('run', [' '.join(args)], host=host, 
                               timeout=timeout)
    if echo:
        print 'EXEC_DAEMON: launched', args, 'as', process, 'on', host
    if not wait:
        return
    with time_limit(timeout, 'launch '+' '.join(args)+' on '+host):
        """Has process finished?"""
        while 1:
            result = call_exec_daemon('poll', [process], 
                                      timeout=timeout, host=host,
                                      why=' to complete '+ ' '.join(args))
            if echo:
                print 'EXEC_DAEMON: poll', process, 'returned', result
            if result == 'DONE':
                break
            sleep(1)
        output = call_exec_daemon('log', [process], 
                                  timeout=timeout, host=host), ''
        if echo:
            print 'EXEC_DAEMON: read', len(output), 'bytes of output for', \
                process, 'on', host
            for line in output[0].split('\n'):
                print 'EXEC_DAEMON_OUTPUT:', process, 'on', host, ':', line
        exit_code = call_exec_daemon('returncode', [process], 
                                     timeout=timeout, host=host)
        if echo:
            print 'EXEC_DAEMON: completed', args, 'id', process, \
                'exit code', exit_code
        try:
            call_exec_daemon('cleanup', [process], timeout=timeout, host=host)
        except Fault:
            if echo:
                print 'EXEC_DAEMON: unable to cleanup for', process, 'on', host
        else:
            if echo:
                print 'EXEC_DEAMON: cleaned up', process, 'on', host
    if exit_code != 0 and not ignore_failure:
        raise SubprocessError(exit_code, output[0], output[1])
    
    if word_split:
        output2 = [x.split() for x in output]
    elif split: 
        output2 = [[line.split() for line in x.split('\n')] for 
               x in output]
    elif line_split:
        output2 = [x.split('\n') for x in output]
    else:
        output2 = output
    outv = output2[0]
    return (exit_code, outv) if ignore_failure else outv

