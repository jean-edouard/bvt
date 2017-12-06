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

from src.bvtlib.retry import retry
from twisted.internet import defer
import os, cStringIO
from settings import PXE_DIR, PXE_SERVER, PASSWORD_HASH, \
    RECOVERY_PUBLIC_KEY, RECOVERY_PRIVATE_KEY, BUILD_PATH
from os.path import join, exists, split
from os import unlink
from src.bvtlib.run import isdir, islink, run, isfile, readfile, writefile, \
    SubprocessError
from re import match
from src.bvtlib.exceptions import ExternalFailure
from src.bvtlib.database_cursor import open_state_db
from src.bvtlib.exceptions import ExternalFailure
from subprocess import Popen, PIPE
from infrastructure.xt.get_build_info import get_build_info
from infrastructure.xt.find_build import find_build
from infrastructure.xt.inspect_build import inspect_build, populate
from infrastructure.xt.generate_pxe_files import generate_pxelinux_cfg, \
    atomic_write, write_netboot
from infrastructure.xt.decode_tag import extract_branch
from infrastructure.xt.releases import scan_releases
from src.bvtlib.dhcp import get_addresses
from shutil import copy
from src.bvtlib import mongodb


class InvalidAction(Exception): pass
class UnknownRelease(ExternalFailure):
    """release not known"""

class MissingBootFile(ExternalFailure):
    """A file that was expected in the boot directory was not found there."""

class UnknownBuild(ExternalFailure):
    """build not known"""

class PxeServerDirectoryUnspecified(Exception):
    """PXE server directory unspecified"""

INSTALL_PXE_HEADER = """default openxt-(NO MLE)
timeout 1
prompt 1
 """

INSTALLER_STATUS_REPORT = """<interactive>true</interactive>
HEADLINE<preinstall>#!/bin/ash
ifconfig eth0 up
udhcpc eth0
touch /config/ssh_enabled
/etc/init.d/sshd stop
/etc/init.d/sshd start
</preinstall>
<mode>upgrade</mode>
<primary-disk>sda</primary-disk>
<network-interface mode="dhcp"></network-interface>
<keyboard>us</keyboard>
<enable-ssh>true</enable-ssh>
<password>%s</password>
<recovery-public-key>%s</recovery-public-key>
<recovery-private-key>%s</recovery-private-key>
""" % (PASSWORD_HASH, RECOVERY_PUBLIC_KEY, RECOVERY_PRIVATE_KEY)

PXE_CONFIG_START = """default autotest
prompt 1
timeout 1

label autotest
"""
ANSWERFILE_AMT_ENDING = """
set -x 
set -e
mount -o remount,rw /mnt/part2/dom0
sed -i "1,/class/s/class/bdf/g" /mnt/part2/dom0/usr/share/xenmgr-1.0/templates/default/service-ndvm
sed -i "s/0x0200/0000:%s:00.0/g" /mnt/part2/dom0/usr/share/xenmgr-1.0/templates/default/service-ndvm
echo starting postintall >&2
sed -i -e 's/xencons=xvc0/xencons=xvc0 rw/' /mnt/part2/dom0/usr/share/xenmgr-1.0/templates/*/service-ndvm
sed -i -e 's/SELINUX=enforcing/SELINUX=permissive/' /mnt/part2/dom0/etc/selinux/config
echo 'system_r:sshd_t:s0 sysadm_r:sysadm_t:s0' >> /mnt/part2/dom0/etc/selinux/xc_policy/contexts/users/root
</postinstall>
<postcommit>
echo starting postcommit >&2
set -x
set -e
sed  -i -e \'s/set default=0/set default="XenClient Technical Support Option: Normal Mode with synchronised console"/\' /mnt/part2/dom0/boot/system/grub/grub.cfg
echo finishing postcommit >&2
</postcommit>
"""
ANSWERFILE_ENDING = """
set -x 
set -e
echo starting postintall >&2
mount -o remount,rw /mnt/part2/dom0
sed -i -e 's/xencons=xvc0/xencons=xvc0 rw/' /mnt/part2/dom0/usr/share/xenmgr-1.0/templates/*/service-ndvm
sed -i -e 's/SELINUX=enforcing/SELINUX=permissive/' /mnt/part2/dom0/etc/selinux/config
echo 'system_r:sshd_t:s0 sysadm_r:sysadm_t:s0' >> /mnt/part2/dom0/etc/selinux/xc_policy/contexts/users/root
</postinstall>
<postcommit>
echo starting postcommit >&2
set -x
set -e
sed  -i -e \'s/set default=0/set default="XenClient Technical Support Option: Normal Mode with synchronised console"/\' /mnt/part2/dom0/boot/system/grub/grub.cfg
echo finishing postcommit >&2
</postcommit>
"""

class AmbiguousRequest(Exception):
    """Please specify only one of release or build"""

class InvalidMacAddress(Exception):
    """Mac address is invalid"""

def pxe_filename(dut, mac_address):
    """Work out the full pathname to the file that pxelinux will read from the server"""
    if not PXE_DIR:
        raise PxeServerDirectoryUnspecified()
    if mac_address is None:
        mac_address = get_addresses(dut)
    mac_address_munged = mac_address.lower().replace(':', '-')
    if not match('([0-9a-f]{2}-){5}([0-9a-f]{2})', mac_address_munged):
        raise InvalidMacAddress(mac_address_munged)
    return join(PXE_DIR, 'pxelinux.cfg', '01-'+mac_address_munged)

def pxe_localboot(dut, mac_address):
    os.remove(pxe_filename(dut, mac_address))

class NoTFTPActivityTimeout(Exception):
    pass

class InvalidBuildTree(Exception):
    pass

def last_tftp_file(dut_ip):
    """Return last file accessed by dut_ip"""
    sdb = open_state_db()
    last_file = sdb.select1_field(
        'file', 'tftp WHERE client=%s ORDER BY timestamp DESC LIMIT 1', 
        dut_ip)
    tftp_after = sdb.select1('COUNT(id) FROM tftp', client=dut_ip)[0]
    print 'TFTP:', tftp_after, 'last_file', last_file
    return (last_file, tftp_after)


def wait_for_tftp(dut_ip, predicate):
    """Wait for predicate to hold for the last file accessed
    by dut_ip"""
    _, tftp_before = last_tftp_file(dut_ip)
    def check_tftp():
        """Check TFTP server activtiy"""
        last_file, tftp_after = last_tftp_file(dut_ip)
        print 'TFTPWAIT:', tftp_after, 'was', tftp_before, 'last', last_file
        if tftp_after == tftp_before or not predicate(last_file):
            raise NoTFTPActivityTimeout(tftp_before, tftp_after, last_file)

    retry(check_tftp, timeout=360.0, catch=[NoTFTPActivityTimeout],
          description='wait for TFTP')


def select_build(build, release):
    """Work out build_info for build or release"""
    if release and build:
        raise AmbiguousRequest(build, release)
    if build:
        if isdir(build):
            print 'INFO: using', build, 'directory for build'
            bi = inspect_build(build, None)
            if len(bi) != 1:
                raise InvalidBuildTree(build, len(bi))
        else:
            branch = extract_branch(build)
            print 'HEADLINE: setting PXE to install', build, 'on', branch
            orig_build_directory = find_build(branch, build, 
                                              build_path=BUILD_PATH)
            print 'INFO: build is located at', orig_build_directory
            bi = inspect_build(orig_build_directory, build)
            if bi == []:
                raise UnknownBuild(branch, build, orig_build_directory)
        return bi[0]
    else:
        assert release
        for releasec in scan_releases():
            if releasec['alias'] == release:
                return releasec
        raise UnknownRelease(release)

def select_variant(build_info):
    kent_variant = [v for v in build_info['variants'] if v['kind'] == 'kent']
    plain_variant = [v for v in build_info['variants'] if v['kind'] == 'plain']
    if kent_variant:
        netboot = kent_variant[0]['netboot']
        variant = 'kent'
        print 'INFO: using kent variant'
    else:
        assert len(plain_variant) == 1
        netboot = plain_variant[0]['netboot']
        variant = 'plain'
        print 'INFO: using plain variant'
    return netboot, variant

def secondary_nic_equipped(dut):
    """Query mongo to see if dut has second nic to passthrough to ndvm so
        AMT works."""
    mdb = mongodb.get_autotest()
    dut_doc = mdb.duts.find_one({'name': dut})
    if dut_doc.get('num-nics'):
        return True if dut_doc['num-nics'] == 2 else False

def get_bus(dut):
    """Query mongo for the bus of secondary nic.  If it isn't there, assume
        nic is on bus 01."""
    mdb = mongodb.get_autotest()
    dut_doc = mdb.duts.find_one({'name': dut})
    if dut_doc.get('nic-bus'):
        return dut_doc['nic-bus']
    else:
        return "01"

def set_pxe_build(dut, build=None, release=None, action='install', mac_address=None,
                  build_url=None):
    """Set dut to do action using build when it PXE boots"""
    assert dut
    print 'PXE_INSTALL:', action, 'for', release or build, 'on', dut
    if action == 'boot':
        print 'PXE_INSTALL: booting'
        assert build is None

    print 'PXE_INSTALL: setting PXE auto-run build for', dut, 'to', \
        release or build
    autopxe = pxe_filename(dut, mac_address)
    if exists(autopxe):
        unlink(autopxe)
    print 'INFO: pxe file location is', autopxe
    if build is None and release is None:
        print 'INFO: removing PXE file'
        if exists(autopxe):
            unlink(autopxe)
        return
    ansdir_tftp = join('autotest', dut) 
    ansdir = join(PXE_DIR, ansdir_tftp)
    partial_build_info = select_build(build, release)
    if build_url:
        partial_build_info['NETBOOT_URL'] = build_url
    partial_build_info['TFTP_PATH'] = ansdir_tftp+'/@netboot@'
    build_info = populate(partial_build_info)

    print 'INFO: installing from', build_info['build_directory']
    print 'PXE_INSTALL: build info', build_info
    netboot, variant = select_variant(build_info)

    print 'INFO: answer file TFTP directory path', ansdir_tftp
    atomic_write(autopxe, 'default '+build_info['alias']+('-u' if action=='upgrade' else '') +'\n'+
                 generate_pxelinux_cfg(build_info), verbose=True)
    with file(autopxe, 'r') as fin:
        for line in fin.readlines():
            print 'PXE: PXE line', line
    write_netboot(build_info, ansdir,
                  kind=variant,
                  ansfile_filter=
                  lambda x: INSTALLER_STATUS_REPORT if
                    action == 'ssh' else
                      x.replace('</postinstall>', ANSWERFILE_AMT_ENDING % get_bus(dut) 
                                            if secondary_nic_equipped(dut)
                                            else ANSWERFILE_ENDING),
                  ansfile_glob='*.ans')
    with file(ansdir+'/'+netboot+'/network.ans', 'r') as fin:
        for line in fin.readlines():
            print 'PXE: answerfile line', line
    return build_info
