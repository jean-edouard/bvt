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
from bvtlib import exceptions

class PartitionTooFull(exceptions.ExternalFailure): pass


def wait_to_come_up(machine):
    boot_start = time.time()
    while True:
        try:
            sh_dut= (connection.connect(host=machine,
                                              user='root'))
        except Exception, exc: 
            print 'INFO: unable to connect to dom0 with',exc
            time.sleep(1)
        else: break
        delay = time.time() - boot_start
        print 'INFO: unresponsive after',delay,'seconds'
        if delay > 600: break
    return (sh_dut)


def reboot_test( machine, hours):
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

TEST_CASES = [{'description':'Reboot platform for $(REBOOT) hours',
               'options_predicate' : lambda options: options.reboot,
               'arguments' :  [('machine', '$(DUT)'), ('hours', '$(REBOOT)')],
               'function' : reboot_test, 'trigger':'soakdown'}]

