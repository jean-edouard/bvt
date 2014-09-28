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

import time, re
from src.bvtlib import exceptions
from src.bvtlib.wait_to_come_up import wait_to_come_up, wait_to_go_down
from src.bvtlib.run import run
class PartitionTooFull(exceptions.ExternalFailure): pass


def old_reboot_test( machine, hours):
    duration = float(hours)*60*60
    print 'INFO: reboot loop duration',duration,'seconds'
    start = time.time()
    cycles = 0
    while cycles ==0 or time.time() - start < duration:
        cycles += 1
        print 'INFO: cycle',cycles
        with connection.wait_to_come_up(machine) as sh_dut:
            out,_ = sh_dut.verified_launch('df')
            for line in out.split('\n'):
                match = re.search('([0-9]+)% (/[a-zA-Z/]*)', line)
                if match is None: continue
                percent= int(match.group(1))
                mount = match.group(2)
                print 'INFO:',percent,'% for',mount
                # After a fresh install: 93% for /
                if percent > 95:
                    raise PartitionTooFull(mount,'is now',percent,'% full')
            print 'HEADLINE: dom0 on',machine,'looks fine',
            print (time.time()-start)/3600.0,'hours into test'
            print 'INFO: sending reboot'
            sh_dut.verified_launch('reboot')
            print 'INFO: sleeping to allow reboot to happen'
            time.sleep(10)
        with wait_to_come_up(machine) as sh_dut: pass

def reboot_test(dut, hours):
    duration = float(hours)*60*60
    print 'INFO: reboot loop duration', duration, 'seconds'
    start = time.time()
    cycles = 0
    while cycles == 0 or time.time() - start < duration:
        cycles += 1
        print 'INFO:cycle', cycles
        wait_to_come_up(dut)        #Wait for host to boot
        print 'HEADLINE: dom0 on',dut,'looks fine',
        print (time.time()-start)/3600.0,'hours into test'
        print 'INFO: sending reboot'
        run(['reboot'], host=dut)
        wait_to_go_down(dut)        #Wait for host to go down



def entry_fn(dut, reboot_dur):
    reboot_test(dut, reboot_dur)

def desc():
    return 'Reboot platform for N hours'
