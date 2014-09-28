#!/scratch/autotest_python/bin/python
#
# Copyright (c) 2014 Citrix Systems, Inc.
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

"""Start processes as required"""

from optparse import OptionParser
from bvtlib.mongodb import get_autotest
from os import killpg, fork, execv, waitpid, WNOHANG
from os import setsid, kill, getpid, remove, unlink
from os.path import exists, abspath, split
from signal import signal, SIGCHLD, SIGINT, SIGTERM, SIGKILL
from time import time, sleep, asctime
from syslog import syslog, LOG_ERR
from sys import stderr
from subprocess import call
from socket import gethostname
from sys import argv, executable
from errno import ECHILD, ESRCH
from fcntl import flock, LOCK_EX, LOCK_NB
from traceback import format_exc
from errno import ESPIPE
from pymongo import ASCENDING

SOURCE_TREE = split(abspath(__file__))[0]
DEBUG = '-v' in argv
ONCE = '-o' in argv
ME = gethostname()

def log(*message):
    """Log to stderr and syslog"""
    text = ' '.join(str(x) for x in message)
    syslog(LOG_ERR, text)
    print >> stderr, text

def died(dutdoc, dutstatus):
    """Process for dut descirbed in dutdoc in database and
    dutstatus in memory has died"""
    log('Finished process', dutdoc['name'])
    if 'pid' in dutstatus:
        del dutstatus['pid']

def start(dutdoc, dutstatus):
    """Start a new process"""
    dutstatus['started'] = time()
    log("Starting", dutdoc['name'])
    get_autotest().duts.update({'_id': dutdoc['_id']},
                               {'$set': {'last_launch_time':
                                             dutstatus['started']}})
    try:
        pid = fork()
    except OSError, exc:
        log('fork failed', exc)
        return

    if pid:
        dutstatus['pid'] = pid
        dutstatus['running'] = 1
        log("Started", dutdoc['name'], "as pid", dutstatus['pid'])
        return

    setsid()
    execv(executable, [executable, 
                         SOURCE_TREE+'/launch.py', '-l',
                         '-m', dutdoc['name']])
    exit(1)

def end_process(dutstatus):
    """Mark process as ended"""
    dutstatus['running'] = 0
    if 'pid' in dutstatus:
        del dutstatus['pid']
    dutstatus['ended'] = time()
    get_autotest().duts.update({'_id': dutstatus['_id']},
                               {'$set': {'last_finish_time':
                                             dutstatus['ended']}})

def handle_dut(dutdoc, running):
    """Do the needful to dutdoc"""
    mine = dutdoc.get('control_machine') == ME
    runbvt = dutdoc.get('run_bvt')
    running.setdefault(dutdoc['name'], dict())
    dutstatus = running[dutdoc['name']]
    dutstatus['_id'] = dutdoc['_id']
    time0 = dutstatus.get('started', 0)
    lastrun = time() - time0
    patient = lastrun < 7200
    shouldrun = mine and runbvt and not patient
    if DEBUG:
        print 'inspecting', dutdoc['name'],
        print 'AUTOMATIC' if runbvt else 'MANUAL',
        print 'MINE' if mine else 'ALIEN',
        if time0:
            print '%ds since last run' % (lastrun),
        else:
            print 'NEVER-RUN',
        print 'PATIENT' if patient else 'TIMED-OUT',
        print 'RUNNING' if dutstatus.get('pid') else 'DEAD',
        print 'SHOULDRUN' if shouldrun else 'IDLE',
    if dutstatus.get('pid'):
        try:
            kill(dutstatus['pid'], 0)
        except OSError:
            pidrunning = False
        else:
            pidrunning = True
        if (not patient) or (not (mine and runbvt)) or not pidrunning:
            log('Killing process for', dutdoc['name'], dutdoc['_id'],
                'process group', dutstatus['pid'])

            try:
                killpg(dutstatus['pid'], SIGKILL)
            except OSError as err:
                if err.errno == ESRCH:
                    # okay, process group already gone
                    log('killpg returned ESRCH for PGID',
                        dutstatus['pid'],
                        'on', dutdoc['name'])
                else:
                    log('killpg failed with', err.errno, err)
                    raise
            # if that SIGKILL does not complete before we
            # check the process, we'll end up calling waitpid
            # from sigchld() at the top of the loop and then
            # checking it later
        if not pidrunning:
            log('Child process for', dutdoc['name'], 'with pid',
                dutstatus['pid'], 'has exited (kill 0 returned 0)')
            end_process(dutstatus)
        if not dutstatus['running']:
            died(dutdoc, dutstatus)
    if mine and runbvt and not dutstatus.get('pid'):
        start(dutdoc, dutstatus)

    if DEBUG:
        print dutstatus

def main():
    """Main"""
    call(['pkill', '-f', 'launch.py'])
    running = {}
    def sigchld(*_):
        """Check for children who have exited; called from SIGCHLD and
        regularly"""
        for dutstatus in running.values():
            if dutstatus.get('running'):
                try:
                    status = waitpid(dutstatus['pid'], WNOHANG)
                except OSError as err:
                    if err.errno == ECHILD:
                        status = dutstatus['pid']
                    else:
                        log('waitpid on', dutstatus, 'returned with', 
                            err.errno, err)
                else:
                    if dutstatus['pid'] == status:
                        end_process(dutstatus)
    def medea():
        """Kill my children"""
        for dutstatus in running.values():
            if dutstatus.get('pid'):
                kill(-dutstatus['pid'], SIGKILL)
    def terminate(*args):
        """Time to die"""
        log("shutting down on signal %r" % (repr(args)))
        medea()
    signal(SIGCHLD, sigchld)
    signal(SIGTERM, terminate)
    signal(SIGINT, terminate)
    while 1:
        sleep(1) # to avoid spinning hard if there's a problem running launch.py
        if DEBUG:
            print '----', asctime()
        sigchld()
        try:
            dutdocs = list(get_autotest().duts.find().sort(
                    [('name',ASCENDING)]))
        except Exception as exc:
            log("exception", exc, "reading duts collection")
            sleep(10)
            continue
        for dutdoc in dutdocs:
            handle_dut(dutdoc, running)
        if ONCE:
            break
        sleep(10)


def cmain():
    """Run main and print exceptions"""
    try:
        lmain()
    except:
        for line in format_exc().split('\n'):
            log("ERR", line)

class PidFile(object):
    """Context manager that locks a pid file.  Implemented as class
    not generator because daemon.py is calling .__exit__() with no parameters
    instead of the None, None, None specified by PEP-343.

    Originally from
    http://code.activestate.com/recipes/577911-context-manager-for-a-daemon-pid-file
    """

    def __init__(self, path):
        self.path = path
        self.pidfile = None

    def __enter__(self):
        if exists(self.path):
            log("found existing pid file", self.path)
            try:
                fileobj = file(self.path, 'r')
                content = fileobj.read()
                fileobj.close()
            except IOError:
                log("Cannot read pid file", self.path)
                exit(2)
            log("pid file contents", repr(content))
            try:
                pidv = int(content)
            except ValueError:
                log("Cannot parse existing pid file as an int")
                exit(3)
            try:
                kill(pidv,0)
            except OSError:
                log("pid", pidv, "gone away; deleting stale pid file")
                unlink(self.path)
            else:
                log("pid", pidv, "exists")
                exit(4)
        self.pidfile = open(self.path, "a+")
        log("opened", self.path)
        try:
            flock(self.pidfile.fileno(), LOCK_EX | LOCK_NB)
        except IOError as exc:
            log("unable to lock", self.path, exc)
            raise SystemExit("Already running according to " + self.path)
        log("locked", self.path)
        log("will seek", repr(self.pidfile))
        try:
            try:
                self.pidfile.seek(0)
            except IOError, exc:
                log("seek error", exc.errno)
                # ESPIPE happens sometimes, I've no idea why
                if exc.errno != ESPIPE:
                    raise
            self.pidfile.truncate()
            log("truncated", self.path)
            self.pidfile.write(str(getpid()))
            log("written", self.path)
            self.pidfile.flush()
            log("flush", self.path)
            self.pidfile.seek(0)
            log("written", self.path)
        except:
            for line in format_exc().split('\n'):
                log("ERR", line)
        return self.pidfile

    def __exit__(self, exc_type=None, exc_value=None, exc_tb=None):
        try:
            log("closing", self.path)
            self.pidfile.close()
        except IOError as err:
            # ok if file was just closed elsewhere
            if err.errno != 9:
                raise
        try:
            remove(self.path)
            log("removed", self.path)
        except OSError:
            log("failed to delete", self.path)

def lmain():
    """Run main with lock"""
    with PidFile(options.pid_file):
        main()

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('-v', '--verbose', action='store_true',
                      help='Show extensive debug output')
    parser.add_option('-d', '--daemonize', action='store_true',
                      help='Run as a daemon')
    parser.add_option('-o', '--once', action='store_true',
                       help='Run once only')
    parser.add_option('-p', '--pid-file', metavar='FILE', action='store',
                      help='Use FILE as a lock', default='/var/run/starter.pid')
    options, _ = parser.parse_args()
    if options.daemonize:
        if exists(options.pid_file):
            log('warning:', options.pid_file, 'already exists')
        log("starting daemon mode")
        from daemon import DaemonContext
        with DaemonContext(pidfile=PidFile(PIDFILE)):
            log("in daemon context")
            cmain()
    else:
        lmain()
