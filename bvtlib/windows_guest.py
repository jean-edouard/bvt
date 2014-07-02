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

"""Bundle of functions related to Windows guests"""
from bvtlib.start_vm import start_vm
from bvtlib.call_exec_daemon import call_exec_daemon, Fault
from bvtlib.wait_for_windows import wait_for_windows
from bvtlib.settings import XC_TOOLS_ISO, TOOLS_ISO_FILES
from bvtlib.exceptions import UnableToFindTools
from bvtlib.tools_iso import set_iso
from bvtlib.run import run

def find_tools_iso(host):
    """A tricky safety feature to make sure we install the right ISO """
    for path in TOOLS_ISO_FILES:
        for drive in [chr(ord('A')+n) for n in range(3, 26)]:
            try:
                full = drive+path
                print 'INSTALL_TOOLS: looking for', full, 'on', host
                ret = call_exec_daemon('fileExists', [full], host=host)
                if ret:
                    print 'INSTALL_TOOLS: found tools ISO on', drive, \
                        'return', ret
                    return drive
            except Fault: 
                pass
    raise UnableToFindTools(TOOLS_ISO_FILES)

def make_tools_iso_available(dut, vm_address, vm_name, domain):
    """Return tools ISO drive for VM at vm_address on dut, making it availble
    if necessary."""
    try: 
        tools_iso_drive = find_tools_iso(vm_address)
    except UnableToFindTools:
        pass
    else:
        return tools_iso_drive
    print 'INSTALL_TOOLS: switching ISO to xc-tools.iso'
    run(['xec-vm', '-u', domain['uuid'], 'shutdown'], host=dut)
    set_iso(dut, domain, XC_TOOLS_ISO)
    start_vm(dut, domain['name'])
    wait_for_windows(dut, vm_name)
    return find_tools_iso(vm_address)
