

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

"""Windows VM state transitions"""

from src.bvtlib.call_exec_daemon import run_via_exec_daemon, call_exec_daemon
from src.bvtlib.time_limit import time_limit
from src.bvtlib.wait_for_windows import is_windows_up, wait_for_guest_to_go_down
from src.bvtlib.tslib import find_guest_vms
from src.bvtlib.run import run
from src.bvtlib.start_vm import start_vm
from src.bvtlib import domains
from time import sleep

def wait_for_windows_to_go_down(vm_address, timeout=120, pace=1.0):
    """Return once windows is down; or through a timeout exception"""
    with time_limit(timeout, description='wait for Windows VM at '+
                    vm_address+' to go down'):
        while 1:
            if not is_windows_up(vm_address):
                return
            sleep(pace)

def wait_for_windows_to_come_up(vm_address, timeout=120, pace=1.0):
    """Return once windows is ip; or through a timeout exception"""
    with time_limit(timeout, description='wait for Windows VM at '+
                    vm_address+' to go down'):
        while 1:
            if is_windows_up(vm_address):
                return
            sleep(pace)

def shutdown_windows(vm_address):
    """Shutdown windows VM at vm_addresss, and return once it is down"""
    run_via_exec_daemon(['shutdown', '-s'], 
                        host=vm_address, wait=False)
    wait_for_windows_to_go_down(vm_address)

def standby_windows(vm_address):
    """Put windows VM at vm_address into standby."""
    print 'HEADLINE: runing powerprof.dll SetSupsendState Standby',
    print 'which we think actually hibernates the VM'
    run_via_exec_daemon(['C:\\Windows\\System32\\rundll32.exe', 
                         'powrprof.dll,SetSuspendState', 'Standby'], 
                        host=vm_address, wait=False)
    wait_for_windows_to_go_down(vm_address)

def hibernate_windows(vm_address):
    """Put windows VM at vm_address into standby."""
    run_via_exec_daemon(['C:\\Windows\\System32\\rundll32.exe', 
                         'powrprof.dll,SetSuspendState', 'Hibernate'], 
                        host=vm_address, wait=False)
    wait_for_windows_to_go_down(vm_address)


##### Added for test cases automation - Nyle
# Some of the functions are duplicates, which needs to be merged/removed later 

def wait_for_vms(machine, who='all', timeout=120):
    """wait for vm/vms to come up after a power operation"""
    domlist = find_guest_vms(machine)
    for domain in domlist:
        if who == 'all' or domain['name'] == who:
            vmip = domains.domain_address(machine, domain['name'])
            wait_for_windows_to_come_up(vmip, timeout=timeout)

def vm_shutdown_self(dut, who='all'):
    """shutdown vm/vms from within the VM"""
    domlist = find_guest_vms(dut)
    for domain in domlist:
        if who == 'all' or domain['name'] == who:
            vmip = domains.domain_address(dut, domain['name'])
            call_exec_daemon('run', ['shutdown -s'], host=vmip, timeout=60)
    for domain in domlist:
        if who == 'all' or domain['name'] == who:
            wait_for_guest_to_go_down(dut, domain['name'])

def vm_shutdown_dom0(dut, who='all'):
    """shutdown vm/vms from dom0"""
    domlist = find_guest_vms(dut)
    for domain in domlist:
        if who == 'all' or domain['name'] == who:
            run(['xec-vm', '-n', domain['name'], 'shutdown'], host=dut)
    for domain in domlist:
        if who == 'all' or domain['name'] == who:
            wait_for_guest_to_go_down(dut, domain['name'])

def vm_poweroff(dut, who='all'):
    """force poweroff a VM from domo"""
    domlist = find_guest_vms(dut)
    for domain in domlist:
        if who == 'all' or domain['name'] == who:
            run(['xec-vm', '-n', domain['name'], 'destroy'], host=dut, timeout=20)
    for domain in domlist:
        if who == 'all' or domain['name'] == who:
            wait_for_guest_to_go_down(dut, domain['name'])

def vm_reboot_dom0(dut, who='all'):
    """reboot vm/vms from dom0"""
    domlist = find_guest_vms(dut)
    for domain in domlist:
        if who == 'all' or domain['name'] == who:
            run(['xec-vm', '-n', domain['name'], 'reboot'], host=dut)
            vmip = domains.domain_address(dut, domain['name'])
            wait_for_windows_to_go_down(vmip)
            wait_for_windows_to_come_up(vmip)

def vm_poweron(dut, who='all'):
    """power on vm/vms"""
    domlist = find_guest_vms(dut)
    for domain in domlist:
        if who == 'all' or domain['name'] == who:
            start_vm(dut, domain['name']) 

def vm_resume(dut, vmName):
    """resume vm from sleep"""
    run(['xec-vm', '-n', vmName, 'switch'], host=dut) 

def vm_hibernate_self(dut, who='all'):
    """hibernate vm/vms from within the VM"""
    domlist = find_guest_vms(dut)
    for domain in domlist:
        if who == 'all' or domain['name'] == who:
            vmip = domains.domain_address(dut, domain['name'])
            call_exec_daemon('run', [r'C:\Windows\System32\rundll32.exe powrprof.dll,SetSuspendState hibernate'], host=vmip, timeout=60)
    for domain in domlist:
        if who == 'all' or domain['name'] == who:
            wait_for_guest_to_go_down(dut, domain['name'])

def vm_hibernate_dom0(dut, who='all'):
    """hibernate vm/vms from dom0"""
    domlist = find_guest_vms(dut)
    for domain in domlist:
        if who == 'all' or domain['name'] == who:
            run(['xec-vm', '-n', domain['name'], 'hibernate'], host=dut)
    for domain in domlist:
        if who == 'all' or domain['name'] == who:
            wait_for_guest_to_go_down(dut, domain['name'])

def vm_sleep_dom0(dut, who='all'):
    """sleep vm/vms from dom0"""
    domlist = find_guest_vms(dut)
    for domain in domlist:
        if who == 'all' or domain['name'] == who:
            run(['xec-vm', '-n', domain['name'], 'sleep'], host=dut)
    for domain in domlist:
        if who == 'all' or domain['name'] == who:
            vmip = domains.domain_address(dut, domain['name'])
            wait_for_windows_to_go_down(vmip)

"""must disable hibernate to properly put to sleep, also assumes admin priv"""
def vm_sleep_self(dut, who='all'):
    """sleep vm/vms from within the VM"""
    domlist = find_guest_vms(dut)
    for domain in domlist:
        if who == 'all' or domain['name'] == who:
            vmip = domains.domain_address(dut, domain['name'])
            print "turning off hibernate :" + str(call_exec_daemon(command='run', args=[r'powercfg -h off'], host=vmip, timeout=60))
            sleep(4)
            call_exec_daemon('run', [r'C:\Windows\System32\rundll32.exe powrprof.dll,SetSuspendState sleep'], vmip)
	
def vm_reinstate_hibernate(dut,who='all'):
    """used to reinstate hibernate after vm_sleep_self call"""
    domlist = find_guest_vms(dut)
    for domain in domlist:
        if who == 'all' or domain['name'] == who:
            vmip = domains.domain_address(dut,domain['name'])
            call_exec_daemon('run', [r'powercfg -h on'], vmip)

#####~ Added for test case automation - Nyle
