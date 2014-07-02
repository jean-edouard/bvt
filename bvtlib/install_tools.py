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

"""Install XenClient tools into VM"""

from bvtlib.guest_info import get_system_type
from bvtlib.run import isfile
from bvtlib.domains import find_domain, name_split
from bvtlib.start_vm import start_vm_if_not_running
from bvtlib.settings import XC_TOOLS_ISO
import sys

def _import_module(name):
    __import__(name)
    return sys.modules[name]

def _proxy_call(dut, guest, function_name, *args, **kwargs):
    """Proxy a call to the appropriate module depending on a guest OS"""
    system_type = get_system_type(dut, guest)
    try:
        module = _import_module("bvtlib.install_tools_%s" % system_type)     
        function = getattr(module, function_name)
    except ImportError, AttributeError:
        raise Exception("failed to invoke %s for system_type %s, " \
                        "module not found or function not implemented" \
                        % (function_name, system_type))
    return function(*args, **kwargs)


def install_tools(dut, guest):
    """Install tools on guest on dut"""
    if not isfile(XC_TOOLS_ISO, host=dut):
        raise ToolsIsoMissing(dut, XC_TOOLS_ISO)
    os, name = name_split(guest)
    domain = find_domain(dut, guest)
    start_vm_if_not_running(dut, domain['name'])
    return _proxy_call(dut, name, 'install_tools', dut, name)

def futile(dut, guest, os_name, build, domlist):
    """Would it be futile to install tools?"""
    return _proxy_call(dut, guest, 'futile', dut, guest, os_name, build, domlist)

def tools_install_problems(dut, guest):
    """Return a string describing reasons why the tools install is bad or None
    if it is good for vm_addresss"""
    os_name, name = name_split(guest)
    return _proxy_call(dut, name, 'tools_install_problems', dut, name)
    

TEST_CASES = [{
        'description': 'Install tools for $(OS_NAME)', 'futile':futile, 
        'command_line_options' : ['-t', '--tools'], 'trigger' : 'VM configure', 
        'function': install_tools, 'bvt':True,
        'arguments': [('dut', '$(DUT)'), ('guest', '$(GUEST)')]}]
