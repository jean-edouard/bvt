#
# Copyright (c) 2011 Citrix Systems, Inc.
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

from bvtlib import connection, Session

def prefix_log(prefix):
    def log(x):
        for line in x.split('\n'):
            print prefix+':',line
    return log

class RotatingLog:
    def __init__(self, filename, prefix):
        self.tail = None
        self.latest = None
        self.filename = filename
        self.prefix = prefix
        self.ctime = 0
        self.tail_command = 'tail -f '+self.filename
    
    def tick(self, shell):
        bad, st,_ = shell.maybe_launch("stat -c '%Z' "+self.filename)
        if bad: return
        try:
            ctime = int(st)
        except ValueError:
            print 'bad output',st
            return
        if ctime != self.ctime:
            print 'log',self.filename,'rotated'
            self.kill_tail(shell)
            self.ctime = ctime
        if self.tail is None:
            self.tail = shell.verified_launch(
                self.tail_command, stdout_callback=self.output,
                timeout=24*60*60*365)
    def output(self, text):
        for line in text.split('\n'):
            print self.prefix +': '+line
            self.latest = line
    
    def kill_tail(self, shell):
        self.tail = None
        shell.launch("pkill -f '%s'" % (self.tail_command))
    def shell_lost(self): self.tail = None

instances = 0
class DutMonitor:
    def __init__(self, dut): 
        global instances
        instances += 1
        assert instances == 1, instances
        self.dut = dut
        self.shell = None
        self.udev_process = None
        self.stopped = False
        self.tick_later(0.0)
        self.logs = [RotatingLog('/var/log/xenstored-access.log',
                                 'XENSTORED'),
                     RotatingLog('/var/log/messages', 'SYSLOG')]
    def tick_later(self, delay): 
        if not self.stopped: 
            reactor.callLater(delay,  self.tick) # pylint: disable=E1101
    
    def tick(self):
        if self.stopped: return
        self.tick_later(2.0)
        shell = self.shell
        if shell is None:
            print 'DUTMONITOR:', 'trying to connect to',self.dut 
            try:
                shell = (connection.connect(
                        host=self.dut, user='root',
                        timeout=2.0,
                        lost_callback=self.shell_lost))
            except error.TCPTimedOutError: 
                print 'DUTMONITOR: unable to connect (TCP timeout)'
            except error.ConnectionRefusedError:
                print 'DUTMONITOR: unable to connect (connection refused)'
            except connection.SSHTransportTimeout:
                print 'DUTMONITOR: unable to connect (SSH timeout)'
            else:
                print 'DUTMONITOR: connection established'
                self.shell = shell
        if shell is None: return
        for log in self.logs: log.tick(self.shell)
        _, load,_ =shell.maybe_launch('cat /proc/loadavg')
        _, uptime,_ = shell.maybe_launch('cat /proc/uptime')
        print 'DUTMONITOR:', 'load=%r uptime=%r' %(load,uptime )
        if self.udev_process is None:
            self.udev_process = self.shell.verified_launch(
            'udevadm monitor --kernel --udev', timeout=24*60*60*365,
            stdout_callback = prefix_log('UDEV')).addErrback(self.lost_udev)
    def shell_lost(self, why):
        self.shell = None
        for log in self.logs: log.shell_lost()
    def lost_udev(self, why):
        print 'INFO: lost udev coverage',why
        self.udev_process = None
    def connect_failure(self, why):
        print 'unable to connect to',self.dut,'reason'
        why.printTraceback()
    
    def destroy(self):
        self.stopped = True
        if self.shell: 
            for log in self.logs: log.tick(self.shell)
            self.shell.drop()
            self.shell = None
        global instances
        instances -= 1

