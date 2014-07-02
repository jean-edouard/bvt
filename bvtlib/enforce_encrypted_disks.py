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

from bvtlib.install_network_test_vm import *
from bvtlib.run import run, writefile

# quoted and used as a parameter to echo:
TEST_PATTERN = 'This is a test pattern'

# ugh.  Can't use writefile as we're trying to write to a block device
TEST_PATTERN_PYTHON = """#!/usr/bin/python
import os.path
assert os.path.exists('/dev/xvdb') and not os.path.isfile('/dev/xvdb')
with open('/dev/xvdb', 'w') as f:
    f.write('""" + TEST_PATTERN + """')"""

# Test failures
class ClearStringFoundInEncryptedDisk(Exception):
    pass

class VMStartedAfterTampering(Exception):
    pass

def test_enforce_encrypted_disks(dut):
    vm = install_network_test_vm(dut, '%s:enforce_encrypted_disks' % NETWORK_TEST_OS_NAME)
    try:
        SIZE = 1 # size of virtual disk for test, in MB

        # 1. Ensure vm is shut-down
        vm.shutdown()

        # 2. Add an encrypted disk.  Start VM, write data to it.  Shut VM down and verify
        #    data is not in the clear
        vhd = run(['xec', 'create-vhd', str(SIZE)], host=dut, timeout=600).strip()
        vm_disk = run(['xec-vm', '-u', vm.uuid, 'add-disk'], host=dut).strip()
        run(['xec', '-o', vm_disk, 'attach-vhd', vhd], host=dut)
        run(['xec', '-o', vm_disk, 'generate-crypto-key', '256'], host=dut, timeout=600)

        # - write the test pattern to the disk
        # sshv4v to the VM would be better but it's incompatible with the current run
        # function so we assume network connectivity thoughout
        vm.start()
        vm_addr = vm.wait_for_guest()
        writefile('testprog', TEST_PATTERN_PYTHON, host = vm_addr)
        run(['python', 'testprog'], host = vm_addr)
        vm.shutdown()

        strings_out = run(['strings', vhd], host = dut).split()
        if True in [TEST_PATTERN in x for x in strings_out]:
            raise ClearStringFoundInEncryptedDisk

        # 3. Replace encrypted disk with an unencrypted one.  Verify VM does not start.
        run(['rm', '-f', vhd], host = dut)
        run(['vhd-util', 'create', '-n', vhd, '-s', str(SIZE)], host = dut)

        try:
            vm.start()
        except:
            pass
        else:
            raise VMStartedAfterTampering

    finally:
        vm.destroy()
        vm.delete()

TEST_CASES = [
    { 
        'description': 'Test that encrypted disks cannot be replaced with unencrypted ones',
        'trigger': 'platform ready', 'bvt': True,
        'function' : test_enforce_encrypted_disks,
        'command_line_options': ['--test-enforce-encrypted-disks'],
        'arguments' : [('dut', '$(DUT)')]
    }
]
