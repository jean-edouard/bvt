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

from time import sleep

def get_boot_time(con):
    timeepoch = None
    problem, out, _ = con.maybe_launch('net statistics server',timeout = 60)
    if problem: print 'BOOT_MONITOR:', 'problem',problem,'getting boot time' 
    else:
        try:
            print 'BOOT_MONITOR:', 'raw output',out 
            uout = out.replace('\r', '')
            lines = out.split('\n')
            timestring= ' '.join(lines[3].split()[2:])
            #  5/4/2010 5:37 PM
            colons = timestring.count(':')
            format = '%m/%d/%Y %I:%M %p' if colons == 1 else '%m/%d/%Y %I:%M:%S %p'
            timetuple = time.strptime(timestring, format)
            timeepoch = time.mktime(timetuple)
            print 'BOOT_MONITOR:', 'epoch',timeepoch 
        except IndexError: pass
    return (timeepoch)

class BootMonitor:
    def __init__(self, con):
        self.con = con
        self.boots = []
    
    def get_first_boot_time(self):
        while True:
            epoch = get_boot_time(self.con)
            if epoch is not None: break
            
            print 'BOOT_MONITOR:', 'boot time not available yet' 
            sleep(1)
        assert epoch > 0
        self.boots.append(epoch)
    
    def get_boot_time(self):
        t = get_boot_time(self.con)
        if t is None: return
        if t not in self.boots: self.boots.append(t)
        return (t)
    def get_number_of_boots(self): return len(self.boots)
    def render_boot_times(self):
        return 'boot times %r' % ([time.asctime(time.localtime(t)) for 
                                  t in self.boots],)
