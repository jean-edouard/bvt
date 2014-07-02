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

"""Archive the VHD of a machine"""
from bvtlib.run import run
from bvtlib.call_exec_daemon import call_exec_daemon
from bvtlib.domains import find_domain
from time import sleep
from bvtlib.store_artifact import store_client_artifact, store_memory_artifact
from bvtlib.wait_for_windows import wait_for_windows
from bvtlib.settings import VHD_SANS_TOOLS_PATTERN, VHD_WITH_TOOLS_PATTERN
from bvtlib.settings import MAXIMUM_VHD_AGE_DAYS, ARTIFACTS_ROOT
from bvtlib.time_limit import time_limit
from bvtlib.get_build import get_build
from os.path import isfile, islink, split, isdir, join
from os import umask, walk, readlink, unlink, listdir, stat
from bvtlib.retry import retry
from os.path import exists
from time import time
from bvtlib.mongodb import get_autotest, DESCENDING

class VhdNotFound(Exception): 
    """Could not locate VHD"""

class UnexpectedFile(Exception):
    """Did not expect file to exist"""

class MultipleDiskKeys(Exception):
    """Not sure which of the keys to take we know about"""

class VmIsRunning(Exception): 
    """Virtual machine is running"""

def clean_old_vhds():
    """Clean up old VHDs"""
    references = set()

    builddir = VHD_WITH_TOOLS_PATTERN[:VHD_WITH_TOOLS_PATTERN.find('%')-1]
    builddocs = get_autotest().builds.find(
        {}, sort=[('build_time', DESCENDING)], limit=5)
    recentbuilds = [bd['_id'] for bd in builddocs]
    builds = listdir(builddir)
    for name in builds:
        if name not in recentbuilds:
            fname = builddir + '/'+ name
            print 'delete', fname
            run(['rm', '-rf', fname], ignore_failure=True)
    
    for (dirpath, dirnames, filenames) in walk('/home/xc_vhds/dev_vhds'):
        for name in filenames:
            full = dirpath+'/'+name
            if not islink(full):
                continue
            references.add(readlink(full))

    print 'INFO: have references to', len(references), 'VHDs'
    for (dirpath, dirnames, filenames) in \
            walk('/home/xc_bvt_output/archive-vhds'):
        for name in filenames:
            full = dirpath+'/'+name
            if full not in references:
                print 'INFO: deleting unreferenced', full
                try:
                    unlink(full)
                except OSError:
                    pass

def get_disk_path(dut, domain):
    pathstr = run(['db-read', '/vm/%s/config/disk/1/path' % (domain['uuid'])], 
                  host=dut)
    spl = pathstr.split()
    if len(spl) != 1:
        raise VhdNotFound(dut, vhdfull)
    return spl[0]

def get_disk_uuid(dut, vhdfull):
    return vhdfull.split('/')[-1].replace('.vhd', '')



def get_disk_key(dut, disk_uuid):
    key_dir = run(['xec', 'get', 'platform-crypto-key-dirs'], 
                  host=dut, word_split=True)[0]
    disk_keys = [join(key_dir, key) for key in 
                 run(['ls', key_dir], word_split=True, host=dut)
                 if key.startswith(disk_uuid)]
    if len(disk_keys) > 1:
        raise MultipleDiskKeys(disk_keys, dut, guest, disk_uuid)
    return disk_keys[0] if disk_keys else None

def archive_vhd(dut, guest, have_tools=None, replace=True, 
                artifact_name = 'archive-vhds', publish=True):
    """Archive the VHD image of guest on dut. have_tools should
    be set iff the XenClient tools are installed for that VHD (since we
    use a separate directory with a symlink name including the build number
    for VHDs with tools"""
    if ARTIFACTS_ROOT is None:
        print 'INFO: artifacts storage disabled'
        return
    domain = find_domain(dut, guest)
    vhd_path = get_disk_path(dut, domain)
    disk_uuid = get_disk_uuid(dut, vhd_path)
    disk_key = get_disk_key(dut, disk_uuid)
    print 'NOTE: disk uuid', disk_uuid, 'key', disk_key
    if have_tools is None:
        from bvtlib.install_tools import tools_install_problems
        have_tools = False if tools_install_problems(dut, guest) else True

    build = get_build(dut)
    key_postfix = (('.'+','.join(disk_key[:-4].split(',')[1:])) if
                   disk_key else '')
    postfix = '.'+domain['name']+ key_postfix + (
        ('.tools.'+build) if have_tools else '.st')+'.vhd'
    print 'HEADLINE: VHD postfix will be', postfix
    info = dict(domain, build=build, encrypted=key_postfix)
    if publish:
        base_file = (VHD_WITH_TOOLS_PATTERN if have_tools else 
                     VHD_SANS_TOOLS_PATTERN) % (info)
        if islink(base_file):
            if not replace:
                print 'ARCHIVE_VHD: already have', base_file
                return
        elif isfile(base_file):
            raise UnexpectedFile(base_file)

    print 'ARCHIVE_VHD: domain state', domain
    if domain['status'] not in ['paused', 'stopped']:
        raise VmIsRunning()
    print 'ARCHIVE_VHD: vhd at', vhd_path

    transfers = {}

    if disk_key:
        keydest = retry(lambda: store_client_artifact(
                dut, disk_key, artifact_name, postfix+'.key'),
                        description = 'store filesystem', timeout=3600, pace=60)
        transfers[keydest] = base_file + '.key'
    vhddest = store_client_artifact(dut, vhd_path, artifact_name, postfix)
    transfers[vhddest] = base_file
    sha = run(['sha256sum', vhddest], timeout=600).split()[0]+'\n'
    shafile = store_memory_artifact(sha, artifact_name, postfix+'.sha256')
    assert isfile(shafile)
    transfers[shafile] =  base_file + '.sha256'
    for destfile in transfers.keys():
        assert isfile(destfile)
    if publish:
        for dest, base_file in transfers.items():
            print 'HEADLINE: publishing', base_file, 'to', dest
            parent = split(base_file)[0]
            umask(0000)
            if not isdir(parent):
                run(['mkdir', '-p', parent])
            run(['ln', '-sf', dest, base_file])
        clean_old_vhds()
    return dest

def have_fresh_vhd(os_name):
    """Do we have a fresh sans tools VHD for os_name?"""
    sans_tools_vhd = VHD_SANS_TOOLS_PATTERN % {'name': os_name, 'encrypted': ''}
    print 'HEADLINE: sans tools VHD path', sans_tools_vhd
    if exists(sans_tools_vhd):
        age = (time() - stat(readlink(sans_tools_vhd)).st_ctime) / (24*60*60.0)
        print 'INFO: have', sans_tools_vhd, 'age', age, 'days'
        if age > MAXIMUM_VHD_AGE_DAYS:
            print 'HEADLINE: ignoring', sans_tools_vhd, 
            print 'since it is', int(age), \
                '(more than', MAXIMUM_VHD_AGE_DAYS, ') days old'
            return False
        else:
            print 'HEADLINE: falling back to', sans_tools_vhd, 'age', age, 'days'
            return True
    else:
        print 'HEADLINE: no VHD'
        return False


TEST_CASES = [
    {'description': 'Archive VHDs', 'trigger':'VM ready', 
     'command_line_options': ['--archive-vhds'], 'function':archive_vhd,
     'arguments' : [('dut', '$(DUT)'), ('guest', '$(GUEST)')]}]
