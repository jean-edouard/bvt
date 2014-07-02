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

"""Deal with XenClient domains"""
from bvtlib.exceptions import ExternalFailure, VMFailedToShutDown, VMNotRunning
from bvtlib.time_limit import time_limit
from bvtlib.retry import retry
from time import sleep
from bvtlib.run import run, SubprocessError
from bvtlib.dhcp import NoDHCPLease, mac_to_ip_address

class VM:
    """Handle to a VM."""

    def __init__(self, dut, uuid):
        self.dut = dut
        self.uuid = uuid

    def get_name(self):
        return run(['xec-vm', '-u', self.uuid, 'get', 'name'], host = self.dut).strip()

    def start(self):
        run(['xec-vm', '-u', self.uuid, 'start'], host=self.dut)

    def destroy(self):
        destroy_domain(self.dut, self.get_name())

    def shutdown(self):
        shutdown_domain(self.dut, self.uuid)

    def get_state(self):
        return run(['xec-vm', '-u', self.uuid, 'get', 'state'], host = self.dut).strip()

    def get_domid(self):
        domid_s = run(['xec-vm', '-u', self.uuid, 'get', 'domid'], host=self.dut).strip()
        domid = int(domid_s)
        if domid == -1:
            raise VMNotRunning
        else:
            return domid

    def wait_for_guest(self):
        assert False, "unimplemented"

    def delete(self):
        run(['xec-vm', '-u', self.uuid, 'delete'], host = self.dut)

def lstrip(param): 
    return [ ' '.join(i.split()) for i in param]

def list_vms(dut, timeout=10):
    # not all the dbus objects appear at once so shortly after xenmgr starts
    # xec-vm can fail
    stdout_capture = retry(
            lambda: run(['xec-vm'], timeout=timeout, host=dut),
            description = 'list VMs',
            timeout=timeout, catch=[SubprocessError])
    lines = [lstrip(line.split('|')) for line in stdout_capture.split('\n')]
    domains = [dict(zip ( ['dom_id', 'name', 'uuid', 'status'], line)) for
               line in lines[1:-1]]
    print 'DOMAINS:', domains
    domains2 = []
    for domain in domains:
        if domain.get('name', '') == '': 
            if not domain.get('dom_id',''). startswith('-'*5):
                print 'DOMAINS:', 'filtered out bogus looking', domain
        else:
            domains2.append(domain)
    return domains2

class CannotFindDomain(ExternalFailure): 
    pass

def name_split(guest):
    """Returns an OS and name from a string of the form os:name or os."""
    colspl = guest.split(':')
    name = ':'.join(colspl[1:]) or guest
    os_name = colspl[0]
    return os_name, name


def find_domain(machine, guest):
    """Find guest domain by name on machine"""
    _, name =  name_split(guest)
    print 'DOMAINS: looking for domain', name
    for candidate in list_vms(machine):
        if name.lower() == candidate.get('name','').lower():
            print 'DOMAINS: mapped', name, 'to', candidate
            return candidate
    print 'DOMAINS: could not find', name, 'on guest'
    raise CannotFindDomain(machine, name, 'specified as', guest)

def wait_for_ip_address(mac, timeout=7200, description=None):
    """Return IP address for mac, waiting for it if necessary"""
    return retry(lambda: mac_to_ip_address(mac, timeout, description), 
                 'find IP address',
                 catch=[NoDHCPLease], timeout=timeout, pace=10.0)

def domain_address_from_uuid(machine, guest_uuid, timeout=60, nic=0):
    """Return the address of guest on machine, within timeout"""
    guest_mac = run(['xec-vm', '-u', guest_uuid, '--nic', str(nic), 'get', 
                     'mac-actual'], host=machine, word_split=True)[0]
    guest_ip = wait_for_ip_address(guest_mac, timeout=timeout,
                                   description=guest_uuid+' on '+machine)
    print 'DOMAINS: found address', guest_ip, 'for', guest_uuid, 'on', machine
    return guest_ip

def domain_address(machine, guest, timeout=60, nic=0):
    """Return the address of guest on machine, within timeout"""
    domain = find_domain(machine, guest)
    return domain_address_from_uuid(machine, domain['uuid'], timeout, nic)

def remove_named_guest(dut, guest):
    """Remove guest from dut"""
    _, name = name_split(guest)
    for domain in list_vms(dut):
        remove = domain.get('name') == name
        print 'INSTALL_GUEST: domain', domain, 'REMOVE' if remove else 'KEEP'
        if remove: 
            if domain.get('status') == 'running':
                print 'DOMAINS: stopping', domain, 'on', dut
                run(['xec-vm', '-n', domain['name'], 'shutdown'], host=dut, timeout=600)
            print 'DOMAINS: deleting', domain
            run(['xec',
                 '-s','com.citrix.xenclient.xenmgr',
                 '-i', 'com.citrix.xenclient.xenmgr.unrestricted',
                 '-o', '/',
                 'unrestricted-delete-vm', domain['uuid']],
                host=dut,
                timeout=600)

def destroy_domain(dut, guest):
    """Destroy guest on dut; this just shuts it down"""
    _, name = name_split(guest)
    run(['xec-vm', '-n', name, 'destroy'], host=dut, timeout=600)

def shutdown_domain(dut, vm_uuid):
    """Attempt to cleanly shut down a VM.  Requires tools to be installed."""
    run(['xec-vm', '-u', vm_uuid, 'shutdown'], host=dut, timeout=600)
    for _ in range(30):
        sleep(5)
        state = run(['xec-vm', '-u', vm_uuid, 'get', 'state'], host=dut, timeout=600)
        if state.strip() == 'stopped':
            return
    raise VMFailedToShutDown

def wait_for_vm_to_stop(dut, guest, timeout=120, pace=5.0):
    """Wait for guest to be marked stopped"""
    with time_limit(timeout, 
                    description='Wait for '+guest+' to be marked as stopped'):
        while 1:
            status = find_domain(dut, guest)
            if status['status'] == 'stopped':
                return
            sleep(pace)

def wait_for_domid_change(dut, guest, old_dom_id, timeout=300, pace=5.0):
    """Wait for guest to change from old_dom_id"""
    with time_limit(timeout,
                    description='Wait for '+guest +
                    ' to change domain ID from '+str(old_dom_id)):
        while 1:
            status = find_domain(dut, guest)
            print 'DOMAINS:', guest, 'dom ID', status['dom_id'], 'c/w', old_dom_id
            if status['dom_id'] != old_dom_id:
                return
            sleep(pace)
