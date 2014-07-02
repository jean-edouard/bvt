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

"""Start guest on dut"""
from bvtlib.run import run, SubprocessError
from bvtlib.wait_for_guest import wait_for_guest
from bvtlib.domains import name_split, list_vms
from bvtlib.guest_info import get_default_exec_method

class InsufficientMemoryToRunVM(Exception):
    """We detected an insufficient memory error when doing xec-vm start"""

class NoVmsToStopToReleaseMemeory(Exception):
    """We wanted to stop domains to release memory for a new VM but none were suitable"""


def start_vm(dut, guest, may_already_be_running=False, timeout=600,
             busy_stop=False, check_method=None):
    """Start guest on dut"""
    check_method = check_method or get_default_exec_method(dut, guest)
    _, name = name_split(guest)
    print 'START_VM:', guest, '->', name
    for i in range(3, 0, -1):
        try:
            run(['xec-vm', '-n', name, 'start'], timeout=600, host=dut)
        except SubprocessError, exc:
            if 'VM is already created' in repr(exc) and may_already_be_running: 
                print 'START_VM:', guest, 'is already running'
            elif 'Not enough free memory!' in repr(exc):
                print 'START_VM: not enough memory at the moment to run', \
                    guest, busy_stop
                if (not busy_stop) or i == 1:
                    raise InsufficientMemoryToRunVM(dut, guest, busy_stop)
                do_busy_stop(dut, guest)
            else: 
                raise
        else:
            break
    run(['xec-vm', '-n', name, 'switch'], host=dut)
    print 'HEADLINE:', guest, 'started and switched to'
    r = wait_for_guest(dut, guest, check_method, timeout=timeout)
    print 'START_VM:', guest, 'responded'
    return r

def start_vm_if_not_running(dut, guest, timeout=600, busy_stop=False):
    """Start guest if it is not already running on dut"""
    _, name = name_split(guest)
    for domain in list_vms(dut, timeout=timeout):
        if domain['name'] == name and domain['status'] == 'running':
            print 'START_VM:', dut, 'on', guest, 'already running'
            return
    print 'START_VM:', dut, 'on', guest, 'not running'
    try:
        return start_vm(dut, guest, timeout=timeout, busy_stop=busy_stop)
    except InsufficientMemoryToRunVM:
        if not busy_stop:
            raise

def do_busy_stop(dut, name):
    """Stop a VM at random to make space for VM name

    Note: this is flawed; we are duplicating code with xenmgr. Maybe instead
    launch VMs and do the evict if we get an out of memory error."""
    domlist = list_vms(dut)
    print domlist
    for domain in domlist:
        domname = domain['name'].lower()
        running = domain['status'] == 'running'
        suitable = domname != 'uivm'
        other = domain['name'] != 'name'
        print 'INSTALL_GUEST: considering hibernation', \
            'OTHER' if other else 'TARGET', \
            'RUNNING' if running else 'STOPPED', \
            'SUITABLE' if suitable else 'UNSUITABLE', domain

        if domain['name'] != name and running and suitable and domain['name'] not in ['ndvm']:
            print 'INSTALL_GUEST: hibernating', domain, 'to make space'
            run(['xec-vm', '-n', domain['name'], 'hibernate'], host=dut)
            return

    raise NoVmsToStopToReleaseMemeory(dut, domlist, name)
        
