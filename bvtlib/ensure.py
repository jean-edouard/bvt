#
# Copyright (c) 2014 Citrix Systems, Inc.
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

"""Ensure VM with tools is running"""
from bvtlib.start_vm import start_vm, InsufficientMemoryToRunVM
from bvtlib.domains import name_split, find_domain, CannotFindDomain
from bvtlib.wait_for_guest import wait_for_guest
from bvtlib.install_tools import tools_install_problems, install_tools
from bvtlib.install_tools_windows import kill_prompt_remover
from bvtlib.install_guest import install_guest, download_image
from bvtlib.install_guest import create_vm
from bvtlib.archive_vhd import have_fresh_vhd
from bvtlib.settings import VHD_WITH_TOOLS_PATTERN, VHD_SANS_TOOLS_PATTERN, \
    MAXIMUM_VHD_AGE_DAYS
from bvtlib.retry import retry
from os.path import exists
from os import stat
from time import time
from bvtlib.get_build import try_get_build
from bvtlib.guest_info import get_system_type
from socket import error

class ToolsNotInstalledInImage(Exception):
    """The canned image did not appear to have tools installed"""
    
def maybe_kill_prompt_remover(dut, guest, vm_address):
    """Kill prompt remover if machine is a win guest"""
    if get_system_type(dut, guest) == "windows":
        kill_prompt_remover(vm_address)

def ensure(dut, guest, busy_stop=True):
    """Ensure guest is installed with tools on dut.
    If busy_stop is true and then shut down other VMs to make more memory"""
    print 'INFO: contacting and determining build on', dut
    build = try_get_build(dut)
    os_name, name = name_split(guest)
    try:
        print 'INFO: looking for domain', guest
        domain1 = find_domain(dut, guest)
    except CannotFindDomain:
        print 'INFO:', guest, 'does not exist yet'
    else:
        print 'INFO: found domain', domain1
        if domain1['status'] != 'running':
            print 'INFO: starting', guest
            vm_address = start_vm(dut, guest, busy_stop=busy_stop)
        else:
            print 'INFO: contacting', guest
            vm_address = wait_for_guest(dut, name)
        problems = tools_install_problems(dut, guest)
        if problems is None:
            print 'HEADLINE: already have suitable VM with tools'
            maybe_kill_prompt_remover(dut, guest, vm_address)
            return vm_address
        else:
            print 'HEADLINE: already have', guest, 'but', problems
            install_tools(dut, guest)
            maybe_kill_prompt_remover(dut, guest, vm_address)
            return vm_address

    with_tools_vhd = VHD_WITH_TOOLS_PATTERN % {'build':build, 'name': os_name, 
                                               'encrypted':''}
    suitable = exists(with_tools_vhd)
    if suitable:
        age = (time() - (stat(with_tools_vhd).st_ctime)) / (24*60*60.0)
        print 'INFO: found prepared VHD', with_tools_vhd, 'which is', age, 'days old'
        if age > MAXIMUM_VHD_AGE_DAYS:
            print 'INFO: not using ready made VHD since it is', age, 'days old'
            valid = False
        else:
            valid = True
    else:
        valid = False
    if valid:
        print 'HEADLINE: have ready made VHD at', with_tools_vhd
        vhd_path_callback = lambda vhd_path: download_image(
            dut, 'with_tools', os_name, vhd_path)
        vm_address2 = create_vm(dut, guest, 
                                vhd_path_callback=vhd_path_callback)
        problem = retry(lambda: tools_install_problems(dut, guest),
              description='determine whether tools are installed',
              catch=[error])
        if problem is not None:
            raise ToolsNotInstalledInImage(with_tools_vhd, problem)
        maybe_kill_prompt_remover(dut, guest, vm_address2)
        return vm_address2
    sans_tools_vhd = VHD_SANS_TOOLS_PATTERN % {'name': os_name, 'encrypted': ''}
    kind2 = 'vhd' if have_fresh_vhd(os_name) else 'iso'
    install_guest(dut, guest, kind2, busy_stop=True)
    install_tools(dut, guest)        
    
TEST_CASES = [
    { 'description': 
      'Ensure that $(OS_NAME) with tools is running', 
      'trigger' : 'VM install',
      'function' : ensure,
      'command_line_options': ['-e', 
                               '--ensure-virtual-machine-with-tools-running'],
      'arguments' : [('dut', '$(DUT)'), ('guest', '$(GUEST)')]}]

