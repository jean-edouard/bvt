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

"""Install .NET using exec daemon"""
from src.bvtlib.call_exec_daemon import call_exec_daemon, run_via_exec_daemon, \
    Fault, SubprocessError
from src.bvtlib.domains import find_domain
from src.bvtlib.settings import DOTNET_4_KEY, DOTNET_4_NAME
from socket import error
from src.bvtlib.wait_for_windows import wait_for_windows
from src.bvtlib.retry import retry
from src.bvtlib.reboot_windows_vm import reboot_windows_vm
from src.bvtlib.wait_for_windows import ensure_stable
from src.bvtlib.windows_guest import make_tools_iso_available
from xmlrpclib import Fault

class UnableToInstallDotNet(Exception): 
    """Unable to install .Net"""

def is_dotnet_installed(vm_address):
    """Return true if the dot net version the tools require is installed"""
    try:
        value = call_exec_daemon('regLookup',  
                                 ['HKLM', DOTNET_4_KEY, DOTNET_4_NAME],
                                 host=vm_address)
    except Fault:
        print 'INFO: .NET key not found on', vm_address
        return False
    print 'INFO: .NET key found with value', value, 'on', vm_address
    return True

def install_dotnet(dut, vm_address, guest):
    """Install dotnet on guest """
    ensure_stable(vm_address, 5, description=guest+' on '+dut)
    if is_dotnet_installed(vm_address):
        print 'INFO: already have .NET installed'
        return
    domain = find_domain(dut, guest)
    print 'HEADLINE: installing .NET'

    try:
        tools_iso_drive = make_tools_iso_available(dut, vm_address, guest, domain)
        run_via_exec_daemon(['%s:\\windows\\dotNetFx40_Full_x86_x64.exe' %tools_iso_drive, '/passive'], timeout=3600, 
                            host=vm_address)
    except (error, Fault):
        wait_for_windows(dut, guest)
    except SubprocessError, exc:
        if exc.args[0] == 3010:
            print 'INFO: dotnet installer indicated reboot required'
    
    reboot_windows_vm(dut, guest)
    ensure_stable(vm_address, 5, description=guest+' on '+dut)
    if not is_dotnet_installed(vm_address):
        raise UnableToInstallDotNet(dut, vm_address, guest)
    print 'HEADLINE: installed .NET'
