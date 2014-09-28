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

"""Reboot a windows VM and wait for that to happen"""
from src.bvtlib.run import run
from src.bvtlib.call_exec_daemon import run_via_exec_daemon
from src.bvtlib.domains import name_split, wait_for_domid_change, find_domain

def reboot_windows(dut, domain, vm_address):
    run_via_exec_daemon(['shutdown', '-f', '-r', '-t', '00'], host=vm_address, wait=False)
    wait_for_domid_change(dut, domain['name'], domain['dom_id'])

def reboot_windows_vm(dut, domain):
    """Triger a reboot of guest"""
    _, name = name_split(domain)
    domain = find_domain(dut, name)
    print 'INFO: rebooting guest', domain
    run(['xec-vm', '-n', name, 'reboot'], host=dut)
    wait_for_domid_change(dut, name, domain['dom_id'])
    print 'INFO: reboot of', domain, 'completed'
