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

"""Bundle of functions related to Linux guests"""
from bvtlib.run import run
from bvtlib.settings import XC_TOOLS_ISO
from bvtlib.exceptions import UnableToFindTools
from bvtlib.tools_iso import set_iso
from bvtlib.start_vm import start_vm
from bvtlib.wait_for_guest import wait_for_guest
from bvtlib.domains import domain_address, find_domain, wait_for_domid_change

def list_cd_devices(host):
    return run(['sh', '-c', 'echo $0', 'sr[0-9]*'], cwd='/dev', host=host, check_host_key=False).split()

def file_exists(host, file_name):
    _, result = run(['test', '-e', file_name], host=host, ignore_failure=True, check_host_key=False)
    return result == 0

def mount_tools_iso(host):
    cd_devices = list_cd_devices(host)
    for device in cd_devices:
        mount_point = '/mnt/%s' % device
        device_path = '/dev/%s' % device
        run(['mkdir', '-p', mount_point], host=host, check_host_key=False)
        msg, code = run(['mount', device_path, mount_point], host=host, ignore_failure=True, check_host_key=False)
        if code != 0:
            print 'INSTALL_TOOLS: mount on', host, 'failed with', msg
            continue
        for path in ['cit.cert', 'linux/install.sh', 'xenclient.ico', 'Packages/XenClientTools.msi']:
            full = "%s/%s" % (mount_point, path)
            print 'INSTALL_TOOLS: looking for', full, 'on', host
            if file_exists(host, full):
                return mount_point
        run(['umount', mount_point], host=host, check_host_key=False)
    raise UnableToFindTools()

def create_file(host, file_name, content):
    run(['dd', 'of=%s' % file_name], host=host, stdin_push=content, check_host_key=False)

def make_tools_iso_available(dut, vm_address, vm_name, domain):
    """Return tools ISO mount point for VM at vm_address on dut, making it
    availble if necessary."""
    try:
        tools_iso_mount_point = mount_tools_iso(vm_address)
    except UnableToFindTools:
        pass
    else:
        return tools_iso_mount_point
    print 'INSTALL_TOOLS: switching ISO to xc-tools.iso'
    run(['xec-vm', '-u', domain['uuid'], 'shutdown'], host=dut, check_host_key=False)
    set_iso(dut, domain, XC_TOOLS_ISO)
    start_vm(dut, domain['name'], check_method='ssh')
    wait_for_guest(dut, vm_name, method='ssh')
    return mount_tools_iso(vm_address)


def soft_reboot(dut, vm_name):
    domain = find_domain(dut, vm_name)
    print 'INFO: rebooting guest', domain
    vm_address = domain_address(dut, vm_name)
    run(['shutdown', '-r', 'now'], host=vm_address, check_host_key=False)
    wait_for_domid_change(dut, vm_name, domain['dom_id'])

def soft_reboot_and_wait(dut, vm_name):
    soft_reboot(dut, vm_name)
    wait_for_guest(dut, vm_name, method='ssh')
