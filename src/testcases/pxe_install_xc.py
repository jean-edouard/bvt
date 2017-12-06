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
from src.bvtlib.exceptions import ExternalFailure
from src.bvtlib.set_pxe_build import pxe_localboot, set_pxe_build, select_build, select_variant
from src.bvtlib.mongodb import get_autotest
from src.bvtlib.power_control import power_cycle
from src.bvtlib.dhcp import get_addresses
from src.bvtlib.wait_to_come_up import wait_to_come_up, is_installer_running
from src.bvtlib.get_build import get_build_number_branch
from src.bvtlib.run import readfile, writefile, run
from src.bvtlib.power_control import wait_to_go_down, platform_transition
from multiprocessing import Process
from src.bvtlib.run import SubprocessError
from time import sleep
from src.bvtlib.filesystem_write_access import FilesystemWriteAccess
from src.bvtlib.temporary_web_server import TemporaryWebServer
from os.path import isdir
from urllib import urlopen
from src.bvtlib.settings import DEFAULT_POWER_CONTROL


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

def pxe_install_xc(dut, build=None, release=None, watch_tftp=None, upgrade=False,
                   mac_address=None):
    """PXE install build on dut"""
    print 'HEADLINE:', 'upgrading' if upgrade else 'installing', \
        release or build, 'XT on', dut
    if watch_tftp is None:
        watch_tftp = 'autotest' in gethostname()
    if isdir(build):
        repository_directory = build+'/repository'
    else:
        build_info = select_build(build, release)
        netboot, variant = select_variant(build_info)
        repository_directory = build_info['build_directory']+'/repository'
        if variant == 'kent':
            repository_directory += '-kent'
        print 'INFO: bi=', build_info, repository_directory

    with TemporaryWebServer(path=repository_directory) as web:
        out = urlopen(web.url+'/packages.main/XC-PACKAGES').read()
        print 'INFO: XC-PACKAGES is', repr(out)
        target_build_info = set_pxe_build(dut, build=build, release=release, 
                        action='upgrade' if upgrade else 'install',
                                            mac_address=mac_address,
                                            build_url = web.url)
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
            print 'INFO: Waiting to come up in installer'
            print 'INFO: ', dut
            wait_to_come_up(dut, installer_okay=True, timeout=120)
            print 'INFO: passed wait to come up'
            if DEFAULT_POWER_CONTROL == 'AMT':
                if not is_installer_running(dut+'-amt', timeout=60):
                    raise PlatformCameUpInsteadOfInstaller(dut)
            else:
                if not is_installer_running(dut, timeout=60):
                    raise PlatformCameUpInsteadOfInstaller(dut)
            print 'HEADLINE: SSH response from installer'
            pxe_localboot(dut, mac_address)
            print 'INFO: set PXE back to default'
            wait_to_come_up(dut, installer_okay=False, timeout=300)
            print 'INFO: response from', dut
            if not isdir(build):
                found = get_build_number_branch(dut, timeout=3600)
            else:
                found = True
        finally:
            process.terminate()
    if found == True:
        pass
    elif found:
        bn, br= found
        print 'PXE_INSTALL:', dut, 'now has', bn, br, 'installed'
        tag = build if build else (target_build_info['tag'] if 
                                   target_build_info and target_build_info.get('tag') else None)
        if tag and (bn not in tag or br not in tag):
            raise UnexpectedInstallAfterInstallation(
                'found=', bn, br, 'wanted=', build, 'on', dut)
    else:
        raise UnableToContactAfterInstallation('wanted=',build,'on',dut)
    print 'HEADLINE: succesfully', 'upgraded' if upgrade else 'installed', \
        (release or build), 'on', dut


def entry_fn(dut, build, mac_address):
    pxe_install_xc(dut, build, False, mac_address)

def desc():
    return 'PXE install XT'
