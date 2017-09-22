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

"""Install XenClient tools into Linux VM"""
from src.bvtlib.domains import find_domain
from src.bvtlib.start_vm import start_vm_if_not_running
from src.bvtlib.wait_for_guest import wait_for_guest
from src.bvtlib.linux_guest import make_tools_iso_available, soft_reboot_and_wait
from src.bvtlib.wait_for_guest import ensure_stable
from src.bvtlib.run import run
from src.bvtlib.domains import domain_address
from src.bvtlib.soft_shutdown_guest import soft_shutdown_guest
from src.testcases.archive_vhd import archive_vhd
from src.bvtlib.exceptions import UnableToInstallTools, ToolsAlreadyInstalled
from src.bvtlib.settings import ARCHIVE_TOOLS_INSTALLED_VHDS

XENCLIENT_MODULES = ['xc_ctxusb', 'xc_v4v', 'xc_netfront', 'xc_blkfront', 'xc_xenfs', 'xc_xen']

def check_module_loaded(host, module):
    _, result = run(['grep', '^%s ' % module, '/proc/modules'], host=host, ignore_failure=True, check_host_key=False)
    return result == 0
    
def tools_install_problems(host, guest):
    """Return a string describing reasons why the tools install is bad or None
    if it is good for VM identified by host, guest pair"""
    bad = []
    vm_address = domain_address(host, guest, timeout=5)
    for m in XENCLIENT_MODULES:
        if not check_module_loaded(vm_address, m):
            bad.append("Module %s not loaded" % m)
    if bad == []:
        return
    message = ('tools not considered installed at this point because '+
               ' and '.join(bad))
    print 'INSTALL_TOOLS:', message
    return message

def install_prerequisites(host):
    run(['apt-get', 'install', 'gdebi-core', '-q'], host=host, check_host_key=False)

def run_upgrade(host):
    run(['apt-get', 'update', '-q'], host=host, check_host_key=False)
    run(['apt-get', 'upgrade', '-yq'], host=host, timeout=600, check_host_key=False)
 
def install_tools(dut, guest):
    """Install tools on guest on dut"""
    domain = find_domain(dut, guest)
    start_vm_if_not_running(dut, domain['name'])
    print 'INSTALL_TOOLS: installing tools on', domain
    vm_address = wait_for_guest(dut, guest, method='ssh')
    print 'HEADLINE: contacted', guest, 'and checking for tools'
    if tools_install_problems(dut, guest) is None: 
        raise ToolsAlreadyInstalled(dut, guest, vm_address)
    print 'INSTALL_TOOLS: installing prequisitives', domain
    install_prerequisites(vm_address)
    # there are some graphics gliches if tools installed on non-upgraded system
    print 'INSTALL_TOOLS: running upgrade', domain
    run_upgrade(vm_address)
    print 'INSTALL_TOOLS: upgrade done', domain
    soft_reboot_and_wait(dut, guest) # reboot after ugprade
    mount_point = make_tools_iso_available(dut, vm_address, guest, 
                                               domain)
    domain = find_domain(dut, guest)
    start_vm_if_not_running(dut, domain['name'])
    print 'HEADLINE: tools ISO available on', mount_point
    ensure_stable(vm_address, 30, description=guest+' on '+dut, method='ssh')
    tools_installer = "%s/linux/install.sh" % mount_point
    result = run([tools_installer], host=vm_address, timeout=300, check_host_key=False)
    print 'INSTALL_TOOLS:', domain, 'tools installation complete'
    print 'INSTALL_TOOLS: output was', result
    print 'INSTALL_TOOLS: rebooting', result
    soft_reboot_and_wait(dut, guest) # reboot after ugprade
    print 'INSTALL_TOOLS: reboot completed', result
    ensure_stable(vm_address, 30, description=guest+' on '+dut, method='ssh')
    problems = tools_install_problems(dut, guest)
    if problems:
        print 'HEADLINE:', problems
        raise UnableToInstallTools(problems)
    print 'HEADLINE: tools installed correctly on', guest, 'at', vm_address
    if ARCHIVE_TOOLS_INSTALLED_VHDS:
        soft_shutdown_guest(dut, guest, timeout=600, method="ssh")
        archive_vhd(dut, guest, have_tools=True, replace=False)
    start_vm_if_not_running(dut, guest)

def futile(dut, guest, os_name, build, domlist):
    """Would it be futile to install tools?"""
    try:
        if not tools_install_problems(dut, guest):
            return "already have tools installed"
    except Exception, exc:
        print 'INSTALL_TOOLS: unable to determine if tools install, exception', repr(exc)
        print_exc()
        return "unable to interact with windows VM"
    else:
        print 'INSTALL_TOOLS: tools need to be installed on', dut, guest
