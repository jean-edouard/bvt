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

from src.bvtlib.run import run
from src.bvtlib.guest_ops import create_guest, guest_start, guest_shutdown, guest_destroy, guest_delete, guest_uuid

class VMStartedAfterTampering(Exception):
    pass

def test_enforce_encrypted_disks(dut):
    vm = create_guest(dut, "enforce_enc_disks", "windows")
    try:
        SIZE = 1 # size of virtual disk for test, in MB

        # 1. Ensure vm is shut-down
        guest_shutdown(dut, vm)

        # 2. Add an encrypted disk.  Start and stop VM
        vhd = run(['xec', 'create-vhd', str(SIZE)], host=dut, timeout=600).strip()
        vm_disk = run(['xec-vm', '-u', guest_uuid(dut, vm), 'add-disk'], host=dut).strip()
        run(['xec', '-o', vm_disk, 'attach-vhd', vhd], host=dut)
        run(['xec', '-o', vm_disk, 'generate-crypto-key', '256'], host=dut, timeout=600)
        guest_start(dut, vm)
        guest_shutdown(dut, vm)

        # 3. Replace encrypted disk with an unencrypted one.  Verify VM does not start.
        run(['rm', '-f', vhd], host = dut)
        run(['vhd-util', 'create', '-n', vhd, '-s', str(SIZE)], host = dut)

        try:
            guest_start(dut, vm)
        except:
            pass
        else:
            raise VMStartedAfterTampering

    finally:
        guest_destroy(dut, vm)
        guest_delete(dut, vm)

def entry_fn(dut):
    test_enforce_encrypted_disks(dut)

def desc():
    return 'Test that encrypted disks cannot be replaced with unencrypted ones'
