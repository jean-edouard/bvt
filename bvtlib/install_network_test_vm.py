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

from bvtlib.build_network_test_vm import build_network_test_vm, NETWORK_TEST_OS_NAME
from bvtlib.archive_vhd import have_fresh_vhd, archive_vhd
from bvtlib.soft_shutdown_guest import soft_shutdown_guest
from bvtlib.domains import find_domain, name_split, shutdown_domain, destroy_domain, CannotFindDomain, VM
from bvtlib.install_guest import install_guest
from bvtlib.linux_guest import soft_reboot_and_wait
from bvtlib.run import run
from bvtlib.settings import ARCHIVE_NETWORK_TEST_VHDS
from bvtlib.exceptions import VMNotRunning

import bvtlib.wait_for_guest

class NetworkTestVM(VM):
    def wait_for_guest(self):
        return bvtlib.wait_for_guest.wait_for_guest(self.dut, self.get_name(), 'ssh')

def configure_v4v_rules(dut, guest):
    run(['xec-vm', '-n', guest, 'add-v4v-firewall-rule', '0 -> myself:2222'], host=dut)

def install_network_test_vm(dut, name):
    if not have_fresh_vhd(NETWORK_TEST_OS_NAME):
        print 'HEADLINE: no fresh vhd for %s, building from scratch' % NETWORK_TEST_OS_NAME
        build_network_test_vm(dut, NETWORK_TEST_OS_NAME)
        soft_shutdown_guest(dut, NETWORK_TEST_OS_NAME, method='ssh')
        if ARCHIVE_NETWORK_TEST_VHDS:
            # we cheat about tools here, but we don't care about tools version
            archive_vhd(dut, NETWORK_TEST_OS_NAME, have_tools=False)
        run(['xec-vm', '-n', NETWORK_TEST_OS_NAME, 'delete'], host=dut)

    assert have_fresh_vhd(NETWORK_TEST_OS_NAME) # won't work outside of CBG

    os_name, vm_name = name_split(name)
    assert os_name == NETWORK_TEST_OS_NAME, "Only %s is supported as a network test VM" % NETWORK_TEST_OS_NAME
    vm_uuid = install_guest(dut, guest=name, kind='vhd')
    configure_v4v_rules(dut, vm_name)
    soft_reboot_and_wait(dut, vm_name) # apply v4v rules

    return NetworkTestVM(dut, vm_uuid)
    
TEST_CASES = [
    { 'description': 'Install network test VM', 
      'trigger': 'VM install',
      'function' : lambda dut, name: install_network_test_vm(dut ,name) and None,
      'command_line_options': ['--install-network-test-vm'],
      'arguments' : [('dut', '$(DUT)'), ('name', '$(GUEST)')]}]
