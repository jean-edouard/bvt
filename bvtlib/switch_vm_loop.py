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

"""Switch VMs for a while"""

from bvtlib.run import run, isdir
from bvtlib.domains import list_vms
from bvtlib.exceptions import ExternalFailure
from time import sleep

class GmchAppearedBadTimes(ExternalFailure):
    """Gmch file appeared"""

def switch_vm_loop(dut, cycles=10):
    """Switch VMs for a while"""
    print 'INFO: starting switch loop'
    vms = list_vms(dut)
    for i in range(cycles):
        print 'INFO: Starting switch cycle %d/%d' % (i+1, cycles)
        for vm in vms:
            if not vm['dom_id']:
                return
            run(['xec-vm', '-d', vm['dom_id'], 'switch'], host=dut)
            sleep(2)
            
            badthings = isdir('/var/log/gmch', host=dut)
            if badthings:
                print 'INFO: All gone bad'
                raise GmchAppearedBadTimes(dut, vms, vm, i)

TEST_CASES = [
    { 'description': 'Switch the VM on screen in a loop',
      'trigger': 'platform ready', 
      'function': switch_vm_loop, 'bvt':True,
      'command_line_options': ['--switch-loop'],
      'arguments' : [('dut', '$(DUT)')]},
]
