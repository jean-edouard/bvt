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

"""Provide information about guest"""
from src.bvtlib.run import run

def get_system_type(host, guest):
    out = run(['xec-vm', '-n', guest, 'get', 'os'], host=host)
    return out.strip()

def set_system_type(host, guest, os):
    run(['xec-vm', '-n', guest, 'set', 'os', os], host=host)

def remove_extra_vms(host, vm_list):
    #removes ndvms and uivm from the returned list
    neat_list =[]
    for vm in vm_list:
        if vm == '00000000-0000-0000-0000-000000000001':
            pass
        elif 'true' == run(['xec-vm', '-u', vm ,'get', 'provides-network-backend'], host=host).strip():
            pass
        else:
            neat_list.append(vm)
    return neat_list

def list_vms_uuid(host, remove_extra=True):
    #if you want to avoid nvdm and uivm remove_extra should be true
    vm_list = run(['xec', 'list-vms'], host=host, line_split=True)
    for i in range(0, len(vm_list)):
    #commands makes it start with /vm/ so getting rid of that
    #also since returning files has _ instead of - 
        vm_list[i] = vm_list[i][4:].replace('_', '-')
    for vm in vm_list:
        if vm == '':
            vm_list.remove(vm)
    if remove_extra:
        vm_list = remove_extra_vms(host, vm_list)
    return vm_list

def list_vms_by_name(host):
    vm_list = list_vms_uuid(host,remove_extra=False)
    vm_list_name = []
    for vm in vm_list:
        vm_name = run(['xec-vm', '-u', vm, 'get', 'name'],host=host).strip()
        if vm_name != '':
            vm_list_name.append(vm_name)
    return vm_list_name

def list_domids(host):
    domid_list = run(['xec', 'list-domids'],host=host, line_split=True)
    if '' in domid_list:
        domid_list.remove('')
    return domid_list

def list_ndvms(host):
    vm_list = list_vms_name(host)
    ndvm_list = []
    for guest in vm_list:
        if guest_provides_network_backend(host,guest):
            ndvm_list.append(guest)
    return ndvm_list

def list_domids_from_name_list(host,name_list):
    domid_list = []
    for name in name_list:
        domid_list.append(guest_domid(host,name))
    return domid_list
   
def get_default_exec_method(host, guest):
    system = get_system_type(host, guest)
    if system == "windows":
        return "exec_daemon"
    elif system == "linux":
        return "ssh"
    else:
        raise Exception("No default exec method for %s" % system)

def guest_acpi_state(host,guest, uuid=None):
    return run(['xec-vm','-n',guest,'get','acpi-state'],host=host).strip()

def is_acpi_state(host,guest,state):
    acpi_state = int(guest_acpi_state(host,guest))
    if acpi_state == state:
        return True
    return False

def guest_name_from_uuid(host,uuid):
    name = run(['xec-vm', '-u', uuid, 'get', 'name'],host=host).strip()
    return name

def guest_uuid_from_name(host,name):
    uuid = run(['xec-vm', '-n', name, 'get', 'uuid'],host=host).strip()
    return uuid
 
def guest_ram(host,guest):
    ram = int(run(['xec-vm', '-n', guest, 'get', 'memory'],host=host).strip())
    return ram

def guest_vcpu(host,guest):
    vcpu = int(run(['xec-vm', '-n', guest, 'get', 'vcpus'],host=host).strip())
    return vcpu

def guest_boot_order(host,guest):
    boot_order = run(['xec-vm', '-n', guest, 'get', 'boot'],host=host).strip()
    return boot_order

def guest_stubdom(host,guest):
    stubdom = run(['xec-vm', '-n', guest, 'get', 'stubdom'],host=host).strip()
    return stubdom

def guest_domid(host,guest):
    domid = run(['xec-vm', '-n', guest, 'get', 'domid'],host=host).strip()
    return int(domid)

def guest_provides_network_backend(host,guest):
    backend = run(['xec-vm', '-n', guest, 'get', 'provides-network-backend'],host=host).strip()
    if backend == 'true':
        return True
    return False

def get_num_domain_ids(host):
    """retrieves number of domain ids, including stubdoms"""
    unparsed = run(['xenops', 'list_domains'],host=host,line_split=True)
    return len(unparsed)-2
    #one for the info line, and one for the empty string at the end

def get_largest_domid(host):
    """gets largetest active dom ID, which might not be largest one used"""
    unparsed = run(['xenops', 'list_domains'],host=host,line_split=True)
    first_parse = []
    for line in unparsed:
        first_parse.append(line.split('|'))
    for line in first_parse:
        if line[0].strip() == '' or line[0].strip() == 'id':
            first_parse.remove(line)
    domids = []
    for line in first_parse:
        domids.append(int(line[0].strip()))
    print "DEBUG: returning %d as highest domid" % max(domids)
    return max(domids)

def get_num_vms(host):
    return len(list_vms_uuid(host))

def guest_tools(host,guest):
    tools = run(['xec-vm', '-n', guest, 'get', 'pv-addons'],host=host).strip()
    if tools == 'true':
        return True
    else: 
        return False
