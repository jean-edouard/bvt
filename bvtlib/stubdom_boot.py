#
# Copyright (c) 2012 Citrix Systems, Inc.
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

"""Test VMs still boots with stubdom"""

from bvtlib.run import run
from bvtlib.domains import name_split, domain_address, find_domain
from bvtlib.domains import wait_for_vm_to_stop
from bvtlib.windows_transitions import wait_for_windows_to_come_up
from bvtlib.windows_transitions import shutdown_windows

def stubdom_boot(dut, guest):
    """Test guest still boots on dut when running with studbom"""
    _, name = name_split(guest)
    vm_address = domain_address(dut, guest)
    run(['xec-vm', '-n', name, 'start'], host=dut)
    run(['xec-vm', '-n', name, 'switch'], host=dut)
    wait_for_windows_to_come_up(vm_address)
    shutdown_windows(vm_address)
    wait_for_vm_to_stop(dut, guest)
    status = find_domain(dut, guest)
    print 'INFO: domain status', status
    run(['xec-vm', '-n', name, 'set', 'cd', 'xc-tools.iso'], host=dut)
    run(['xec-vm', '-n', name, 'set', 'stubdom', 'true'], host=dut)
    print 'INFO: booting', guest, 'with stubdom'
    run(['xec-vm', '-n', name, 'start'], host=dut)
    run(['xec-vm', '-n', name, 'switch'], host=dut)
    wait_for_windows_to_come_up(vm_address)
    print 'HEADLINE: verified', guest, 'works with stubdom=true'
    
TEST_CASES = [{
        'description': 'Boot stubdom running $(OS_NAME)', 
        'command_line_options' : ['--stubdom-boot'], 'trigger' : 'VM ready', 
        'function': stubdom_boot, 'bvt':True,
        'arguments': [('dut', '$(DUT)'), ('guest', '$(GUEST)')]}]
