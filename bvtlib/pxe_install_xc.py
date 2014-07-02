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

"""PXE install build on dut"""
from socket import gethostname
from bvtlib.exceptions import ExternalFailure
from bvtlib.set_pxe_build import set_pxe_build
from bvtlib.verify_pxe_rig import verify_pxe_rig
from bvtlib.mongodb import get_autotest
from bvtlib.power_control import power_cycle
from bvtlib.dhcp import get_addresses
from bvtlib.wait_to_come_up import wait_to_come_up, is_installer_running
from bvtlib.get_build import get_build_number_branch
from bvtlib.run import readfile, writefile, run
from bvtlib.power_control import wait_to_go_down, platform_transition
from multiprocessing import Process
from bvtlib.run import SubprocessError
from time import sleep
from filesystem_write_access import FilesystemWriteAccess

class UnexpectedInstallAfterInstallation(ExternalFailure): 
    """Could not complete installation"""

class PlatformCameUpInsteadOfInstaller(ExternalFailure):
    """We were expecting the installer but found the platform"""

class UnableToContactAfterInstallation(ExternalFailure):
    """Could not contact machine after installation"""

def watch(host, filename):
    """Watch filename on host"""
    covered = 0
    while 1:
        try:
            content = readfile(filename, host=host)
        except Exception, exc:
            print 'INSTALLER: contact problem', exc
        else:
            newstuff = content[covered:]
            if newstuff:
                for line in newstuff.split('\n'):
                    print 'INSTALLER:', line
            covered = len(content)
        sleep(2)

def pxe_install_xc(dut, build=None, release=None, watch_tftp=None, upgrade=False):
    """PXE install build on dut"""
    print 'HEADLINE:', 'upgrading' if upgrade else 'installing', \
        release or build, 'XT on', dut
    verify_pxe_rig(dut)
    if watch_tftp is None:
        watch_tftp = 'autotest' in gethostname()
    _, dut_ip = get_addresses(dut)
    print 'PXE_INSTALL: dut IP:', dut_ip, 'for', dut
    dutdoc = get_autotest().duts.find_one({'name':dut})
    target_build_info = set_pxe_build(dut, build=build, release=release, 
                  action='upgrade' if upgrade else 'install')
    print 'PXE_INSTALL: set PXE server'
    if upgrade:
        try:
            platform_transition(dut, 'reboot')
        except SubprocessError:
            print 'HEADLINE: unable to contact', dut, 'to do clean shutodwn'
        else:
            wait_to_go_down(dut)
    power_cycle(dut, pxe=True)
    process = Process(target=watch, args=(dut, '/var/log/installer'))
    process.start()
    try:
        print 'PXE_INSTALL: waiting to come up in installer'
        wait_to_come_up(dut, installer_okay=True, timeout=600)
        if not is_installer_running(dut, timeout=60):
            raise PlatformCameUpInsteadOfInstaller(dut)
        print 'HEADLINE: SSH response from installer'
        set_pxe_build(dut, action='boot')    
        print 'PXE_INSTALL: set PXE back to default'
        wait_to_come_up(dut, installer_okay=True)
        print 'PXE_INSTALL: response from', dut
        found = get_build_number_branch(dut, timeout=3600)
    finally:
        process.terminate()
    if found:
        bn, br= found
        print 'PXE_INSTALL:', dut, 'now has', bn, br, 'installed'
        tag = build if build else (target_build_info['tag'] if 
                                   target_build_info and target_build_info.get('tag') else None)
        if tag and (bn not in tag or br not in tag):
            raise UnexpectedInstallAfterInstallation(
                'found=',bn,br,'wanted=',build,'on',dut)
    else:
        raise UnableToContactAfterInstallation('wanted=',build,'on',dut)
    print 'HEADLINE: succesfully', 'upgraded' if upgrade else 'installed', \
        (release or build), 'on', dut
    get_autotest().duts.update({'name':dut}, {'$unset': {'test_failed':1}})


XT_INSTALL_TEST_CASE = {
    'description' : 'PXE install XT', 
    'trigger': 'platform install',
    'function' : pxe_install_xc, 'bvt':True,
    'command_line_options': ['-X', '-x', '--install-xt'],
    'arguments' : [('dut','$(DUT)'), ('build', '$(BUILD)'), ('release', '$(RELEASE)'),
                   ('upgrade', False)]}


TEST_CASES = [ XT_INSTALL_TEST_CASE,
    {'description' : 'Upgrade XT', 'trigger':'platform install',
     'function' : pxe_install_xc,  'bvt':False,
     'command_line_options': ['-u', '--upgrade-xt'], 
     'arguments' : [('dut','$(DUT)'), ('build', '$(BUILD)'), ('release', '$(RELEASE)'),
                    ('upgrade', True)]}
]
