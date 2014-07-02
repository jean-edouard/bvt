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

from string import rstrip
from bvtlib.run import run, SubprocessError
from bvtlib.domains import name_split, domain_address, wait_for_vm_to_stop, list_vms
from bvtlib.exceptions import ExternalFailure
from bvtlib.wait_for_guest import wait_for_guest

class GuestLeakingLoopbacks(ExternalFailure):
    """When a guest is `power-cycled', it leaves loopback devices behind."""

class VMHasDeadBeef(ExternalFailure):
    """A DEADBEEF marker has been placed in a UUID, indicating a possible zombie."""

class UnclaimedVHD(ExternalFailure):
    """A VHD has been found which is not associated with any VM."""

def list_vm_taps(dut, uuid):
    disk_number = 0
    disk_taps = [ ]
    while True:
        try:
            disk_path = run(['xec-vm', '-u', uuid, '--disk', repr(disk_number), 'get', 'phys-path'], host=dut)
        except SubprocessError:
            break
        disk_number += 1
        disk_taps.append(disk_path.split('\n')[0])
    print 'INFO: disk taps for domain', uuid, 'are', disk_taps
    return disk_taps
    
def start_and_stop_guest(dut, guest):
    print 'INFO: starting guest', guest, 'on', dut
    run(['xec-vm', '-n', guest, 'start'], host=dut)
    run(['xec-vm', '-n', guest, 'switch'], host=dut)
    print 'INFO: waiting for guest', guest, ' to start on', dut
    vm_address = wait_for_guest(dut, guest, 'exec_daemon')
    print 'INFO: shutting down guest', guest, 'on', dut
    run(['xec-vm', '-n', guest, 'shutdown'], host=dut)
    print 'INFO: waiting for guest', guest, 'to stop on', dut
    wait_for_vm_to_stop(dut, guest)

def resource_leakage_test(dut, guest):
    print 'INFO: starting test for guest resource leakage'
    loopback_text = run(['losetup'], host=dut, split=True)
    print 'INFO: loopback text is', loopback_text
    old_loopbacks = len(loopback_text) - 1
    print 'INFO: there are', old_loopbacks, 'loopbacks'
    # there may be a loopback left over from the test framework
    # setting the VM up, so get rid of that
    if old_loopbacks > 0:
        for loopback in loopback_text:
            if len(loopback) > 0:
                loopback_device = rstrip(loopback[0], ':')
                print 'INFO: deleting', loopback_device
                run(['losetup', '-d', loopback_device], host=dut)
        loopback_text = run(['losetup'], host=dut, split=True)
        print 'INFO: new loopback text is', loopback_text
        old_loopbacks = len(loopback_text) - 1
    xec_before_test = run(['xec-vm'], host=dut)
    print 'INFO: before the test, xec showed', xec_before_test
    x, name = name_split(guest)
    print 'INFO: guest is', guest, 'and x is', x, 'and name is', name
    # should shut the VM down first, but how does that interact with getting its address?
    run(['xec-vm', '-n', name, 'shutdown'], host=dut)
    print 'INFO: waiting for guest', name, 'to stop on', dut
    wait_for_vm_to_stop(dut, name)
    start_and_stop_guest(dut, name)
    new_loopbacks = len(run(['losetup'], host=dut, line_split=True)) - 1 
    vm_uuids = [ vm['uuid'] for vm in list_vms(dut) ]
    print 'INFO: vm uuids are', vm_uuids
    known_vm_taps = []
    for uuid in vm_uuids:
        known_vm_taps.extend(list_vm_taps(dut, uuid))
    all_taps = [x[3].split(':')[1]
                for x in run(['tap-ctl', 'list'],
                             host=dut,
                             split=True)
                [:-1]]
    print 'INFO: taps known to belong to vms are', known_vm_taps
    print 'INFO: all taps are', all_taps
    for tap in all_taps:
        if tap not in known_vm_taps:
            raise UnclaimedVHD(tap)
    for uuid in vm_uuids:
        if 'deadbeef' in uuid:
            raise VMHasDeadBeef(uuid )
    print 'INFO: after starting and stopping guest, there are', new_loopbacks, 'loopbacks'
    if new_loopbacks > old_loopbacks:
        raise GuestLeakingLoopbacks(new_loopbacks - old_loopbacks)
    print 'HEADLINE: verified no loopback leakage from guest'

TEST_CASES = [{
        'description': 'Start and stop a guest, and see whether it left any mess behind it.',
        'command_line_options' : ['--vm-resource-leakage'],
        'trigger' : 'VM ready', # TODO: want to assume a guest exists, too
        'function': resource_leakage_test,
        'bvt':True,
        'arguments': [('dut', '$(DUT)'),
                      ('guest', '$(GUEST)')]}]
