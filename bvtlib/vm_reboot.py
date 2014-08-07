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

from bvtlib.reboot_windows_vm import reboot_windows_vm
from bvtlib.windows_transitions import shutdown_windows
from bvtlib.wait_for_windows import wait_for_windows

def vm_reboot_toolstack(dut, guest):
    reboot_windows_vm(dut, guest)

def vm_reboot_guest(dut, guest):
    vm_address = wait_for_windows(dut, guest)
    shutdown_windows(vm_address)

TEST_CASES = [{
        'description': 'Reboot VM in guest', 'trigger':'VM ready',
        'function': vm_reboot_guest, 
        'options_predicate':lambda options: options.vm_reboot_guest,
        'arguments':[('dut', '$(DUT)'), ('guest', '$(GUEST)')]}, {
        'description': 'Reboot VM with toolstack', 'trigger':'VM ready',
        'function': vm_reboot_toolstack, 
        'options_predicate':lambda options: options.vm_reboot_toolstack,
        'arguments':[('dut', '$(DUT)'), ('guest', '$(GUEST)')]}]
