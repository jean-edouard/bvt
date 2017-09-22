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

"""Install VMs"""

from src.bvtlib.domains import name_split, list_vms, \
    domain_address, CannotFindDomain
from src.testcases.archive_vhd import archive_vhd, have_fresh_vhd
from src.bvtlib.run import specify, run
from src.bvtlib.start_vm import start_vm, InsufficientMemoryToRunVM
from src.bvtlib.retry import retry
from src.bvtlib.settings import VHD_SANS_TOOLS_URL, \
    IMAGE_PATHS, VHD_WITH_TOOLS_PATTERN, VHD_SANS_TOOLS_PATTERN, \
    VM_MEMORY_ASSUMED_OVERHEAD_MEGABYTES
from src.bvtlib.mongodb import get_autotest
from src.bvtlib.call_exec_daemon import run_via_exec_daemon
from os.path import isfile, islink, isabs
from multiprocessing import Process
from time import sleep, time
from src.bvtlib.get_build import get_build, try_get_build
from os.path import exists, basename
from src.bvtlib.settings import DISK_ENCRYPTION_KEY_LENGTH
from src.bvtlib.wait_for_guest import ensure_stable
from src.bvtlib.soft_shutdown_guest import soft_shutdown_guest
from src.bvtlib.install_dotnet import install_dotnet
from src.bvtlib.get_xc_config import get_xc_config_field

class IOCorruption(Exception): 
    """The disk md5 sum is not what was exepected"""


class InsufficientStorage(Exception):
    """There is not enough disk space for a new VM"""

class DomainAlreadyExists(Exception):
    """We were asked to install a domain that already exists"""

class NoFreshVHD(Exception):
    """We have no fresh VHD to install"""

class UnableToEstablishMemoryFree(Exception):
    """Unable to parse memory free from xenops physinfo output"""

class InsufficientMemory(Exception):
    """There is not memory free for a new VM"""

def calculate_memory_size(os_name):
    """How much memory do we plan to use for os_name?"""
    if 'win7' in os_name and '64' in os_name:
        return 2048
    return 256 if os_name == 'xp' else 1024

def check_free(dut, amount=10*1000*1000, target_os='win7'):
    """Raise InsufficientStorage if there is less than amount GB free on dut 
    for VHDs"""
    block_size = int(run(['stat', '-f', '/storage', '--printf=%s'],
                         host=dut))
    free_blocks = int(run(['stat', '-f', '/storage', '--printf=%f'],
                          host=dut))
    disk_free = block_size * free_blocks
    memory = calculate_memory_size(target_os)
    print 'HEADLINE: INSTALL_GUEST: free space=%d bytes, %.3fGB'  %(
       disk_free, disk_free/1e9)

    if disk_free < amount:
        raise InsufficientStorage(dut, disk_free)

#    run(['setenforce', '0'], host=dut)
    out = run(['xl', 'info'], host=dut, line_split=True)
#    run(['setenforce', '1'], host=dut)
    megfree = None
    for line in out:
        spl = line.split()
        if len(spl) == 3 and spl[0] == 'free_memory':
            megfree = int(spl[2])
    if megfree is None:
        raise UnableToEstablishMemoryFree(out)
    
    vm_off_mem = 0
    for vm in list_vms(dut):
        # we may double count VMs which are shutting down or starting
        # but that's better than overallocating
        if vm['status'] != 'running':
            vm_mem = run(['xec-vm', '-u', vm['uuid'], 'get', 'memory'],
                         host=dut)
            try:
                vm_off_mem += (int(vm_mem.split()[0]) + 
                               VM_MEMORY_ASSUMED_OVERHEAD_MEGABYTES)
            except ValueError:
                print 'PROBLEM: unable to determine memory used by', \
                    vm, 'get memory output', repr(vm_mem)
    print ('HEADLINE: have %d free memory want %d ' +
           'keep %d for off VMs for %s') % (
        megfree, memory, vm_off_mem, target_os)
    if megfree < memory + vm_off_mem:
        raise InsufficientMemory(megfree, memory, target_os, vm_off_mem)


def watch_space(host, path, period=1.0):
    """Poll disk space on path"""
    first = None
    start = time()
    while 1:
        out = run(['df', path], host=host, verbose=False, split=True)
        value = eval(out[1][2])
        if first is None:
            first = value
        delta = value-first
        deltat = time() - start
        print ('DISKSPACE: path=%s space=%s used=%s increase=%dMB '+ 
            'rate of increase=%.3fMbps') % (
            path, out[1][3], out[1][2], delta/1e3, (delta*8.0)/deltat/1e3)
        sleep(period)

def download_image(dut, kind, guest, dest_file, url=None):
    """Download a standard BVT image"""
    # wget fails if target exists, so make sure it doesn't
    if kind == 'with_tools':
        build = get_build(dut)
    else:
        build = None
    print 'INSTALL_GUEST: downloading', url, 'as', dest_file
    job = specify(host=dut)
    job(['rm', '-f', dest_file])
    watcher = Process(target=watch_space, args=(dut, '/storage'))
    watcher.start()
    print 'INFO: downloading', url, 'to', dest_file
    retry(lambda: job(['wget', '-q', '-O', dest_file, url], timeout=3600),
          timeout=7200, description='download '+url)
    watcher.terminate()
    size = job(['ls', '-l', dest_file], word_split=True)[4]
    print 'INFO: downloaded', size, 'byte', url.split('/')[-1]

def create_vm(dut, guest, encrypt_vhd=False, 
              iso_name=None, vhd_path_callback = lambda x: None,
              start_timeout=1200, busy_stop=False,
              networked=True):
    """Create and boot VM on dut called guest, with access to iso_name
    if specified.  Wait start_timeout for it to boot. Invoke
    vhd_path_callback between creating and booting it with its vhd_path"""
    os_name, name = name_split(guest)
    current = list_vms(dut)
    print 'INFO: have VMs', current
    for already in list_vms(dut):
        if already['name'] == name:
            raise DomainAlreadyExists(dut, guest)

    memsize = 256 if os_name == 'xp' else 1024
    is_windows = not os_name.startswith("ubuntu")
    check_method = "exec_daemon" if is_windows else "ssh"
    go = specify(timeout=120, host=dut)
    dbus_path = go(["xec",  "create-vm"], word_split=True)[0]
    print 'INSTALL_GUEST: dbus path', dbus_path
    vm_go = lambda x: go(['xec', '-o', dbus_path, '-i',
                          'com.citrix.xenclient.xenmgr.vm']+ x, word_split=True)
    vm_go(['set', 'name', name])
    imgpath = IMAGE_PATHS.get(os_name)
    if imgpath:
        vm_go(['set', 'image-path', imgpath])
    # set image-path correctly?
    vm_go(['set', 'memory', str(memsize)])
    vm_go(['set', 'wired-network', 'brbridged'])
    vm_go(['set', 'vcpus', '2'])
    vm_go(['set', 'description', name])
    vm_go(['set', 'stubdom', 'true'])
    if is_windows:
        vm_go(['set', 'os', 'windows'])
    else:
        vm_go(['set', 'os', 'linux'])
        vm_go(['set', 'xci-cpuid-signature', 'true'])
        vm_go(['set', 'viridian', 'false'])
    if iso_name:
        vm_go(['set', 'cd', iso_name])
    if networked:
        nic_list = vm_go(['list-nics'])
        print 'INFO: nic list', repr(nic_list)
        num_existing_nics = len(nic_list)
        no_nics_expected = get_xc_config_field(dut, 'NoDefaultNicsInTemplates', default_value=False)
        print 'INFO: found', num_existing_nics, 'NICs'
        if num_existing_nics == 0: 
            if not no_nics_expected:
                print 'WARNING: No NICs were present on the newly-created VM, but the config file does not indicate that there should be no NICs'
                wired_nic_path = vm_go(['add-nic'])[0]
                wireless = run(['xec', '-o', '/host', 'get', 'wireless-model'], host=dut, word_split=True)
                if len(wireless) > 0:
                    wireless_nic_path = vm_go(['add-nic'])[0]
                    go(['xec', '-o', wireless_nic_path, 'set', 'wireless-driver', 'true'])
                    go(['xec', '-o', wireless_nic_path, 'set', 'network', '/wifi/0/shared'])
                    print 'INFO: wired_nic_path is', wired_nic_path, 'and wireless_nic_path is', wireless_nic_path
                else:
                    print 'INFO: wired_nic_path is', wired_nic_path
                    
        else:
            if no_nics_expected:
                print 'WARNING: Some NICs were present on the newly-created VM, but the config file does not indicate that there should be any NICs'
    vhd_path = go(['xec', 'create-vhd', '80000'], split=True)[0][0]
    print 'INSTALL_GUEST:', 'VHD path', vhd_path
    assert vhd_path.endswith('.vhd')
    print 'INSTALL_GUEST: after configuration %r' % (go(
        ['xec-vm', '-n', name, 'getall']))
    disk_dbus_path = (go(['xec-vm', '-n', name, 'add_disk'], split=True))[0][0]
    disk_number = disk_dbus_path.split('/')[-1]
    print 'INSTALL_GUEST: disk path',  disk_dbus_path, 'number', disk_number
    go(['xec-vm', '-n', name, '--disk', disk_number, 'attach_vhd', vhd_path])
    vhd_path_callback(vhd_path)
    if encrypt_vhd:
        key_dir = run(['xec', 'get', 'platform-crypto-key-dirs'], 
                      host=dut, line_split=True)[0]
        run(['mkdir', '-p', key_dir], host=dut)
        phys_path = run(['xec-vm', '-n', name, '--disk', '1', 
                        'get', 'phys-path'], host=dut, line_split=True)[0]
        print 'INFO: VHD physical path', phys_path
        assert basename(phys_path).endswith('.vhd')
        vm_vhd_uuid = basename(phys_path)[:-4]
        key_file = (key_dir + '/'+vm_vhd_uuid+',aes-xts-plain,'+
                    str(DISK_ENCRYPTION_KEY_LENGTH)+'.key')
        print 'INFO: VHD key', key_file
        # /dev/random can take more than 60 seconds to generate 512 bits
        # of randomness
        run(['dd', 'if=/dev/urandom', 'of='+key_file, 
             'count='+str(DISK_ENCRYPTION_KEY_LENGTH/8), 'bs=1'],
            host=dut)
        run(['vhd-util', 'key', '-n', phys_path, '-k', key_file, '-s'], 
            host=dut)
        print 'INFO: set up encryption'
    else:
        print 'INFO: using an un-encrypted vhd'
    print 'INSTALL_GUEST: starting', guest
    vm_address = start_vm(dut, guest, timeout=start_timeout, 
                          busy_stop=busy_stop, check_method=check_method)
    print 'INSTALL_GUEST: start_vm returned, address', vm_address
    ensure_stable(vm_address, 30, method=check_method, description = guest + ' on '+dut)
    print 'INSTALL_GUEST: VM stable'
    return vm_address

def do_guest_install(dut, kind, guest, encrypt_vhd=False, busy_stop=False, url=None):
    """Inner guest install function"""
    os_name, name = name_split(guest)
    if kind == 'iso':
        iso_file = '/storage/isos/%s.iso' % os_name
        download_image(dut, kind, guest, iso_file, url)
    def vhd_path_callback(vhd_path):
        """vhd_path is now known"""
        if kind in ['vhd', 'with_tools']:
            download_image(dut, kind, guest, vhd_path, url)
    iso_name = ('xc-tools' if kind  != 'iso' else os_name)+'.iso'
    print 'INSTALL_GUEST: using', iso_name, 'for', kind, guest
    vm_address = create_vm(dut, guest, iso_name=iso_name, 
              vhd_path_callback=vhd_path_callback, encrypt_vhd=encrypt_vhd,
              start_timeout=7200 if kind == 'iso' else 1200, 
              busy_stop=busy_stop)
    if kind == 'iso': 
        # this is ugly...
        if os_name.startswith("ubuntu"):
            method = "ssh"
        else:
            method = "exec_daemon"
        # we cannot use xenmgr here as tools are not installed
        soft_shutdown_guest(dut, guest, timeout=600, method=method)
        archive_vhd(dut, guest, have_tools=False)


def futile_iso(dut, guest, os_name, build, domlist):
    """Return None or a reason why doing an ISO install on dut would be 
    futile"""
    with_tools_vhd = VHD_WITH_TOOLS_PATTERN % {'build':build, 'name': os_name,
                                           'encrypted':''}
    if exists(with_tools_vhd):
        return "have VHD with tools available"
    sans_tools_vhd = VHD_SANS_TOOLS_PATTERN % {'name': os_name, 'encrypted':''}
    if have_fresh_vhd(os_name):
        return "have fresh VHD available"
    if os_name in set(dom['name'] for dom in domlist):
        return "already have VM"
    try:
        check_free(dut, target_os=os_name)
    except InsufficientStorage:
        return "insufficient storage for new VM"
    except InsufficientMemory:
        return "insufficient memory for new VM"

def futile_vhd(dut, guest, os_name, build, domlist):
    """Return None or a reason why doing a sans tools VHD install on dut would be 
    futile"""
    if not have_fresh_vhd(os_name):
        return "no fresh enough VHD available"
    if os_name in set(dom['name'] for dom in domlist):
        return "already have VM"
    sans_tools_vhd = VHD_SANS_TOOLS_PATTERN % {'name': os_name, 'encrypted':''}
    if not exists(sans_tools_vhd):
        return "no VHD available"
    with_tools_vhd = VHD_WITH_TOOLS_PATTERN % {'build':build, 'name': os_name,
                                               'encrypted':''}
    if exists(with_tools_vhd):
        return "VHD with tools available"
    try:
        check_free(dut, target_os=os_name)
    except InsufficientStorage:
        return "insufficient storage for new VM"
    except InsufficientMemory:
        return "insufficient memory for new VM"

def futile_with_tools(dut, guest, os_name, build, domlist):
    """Return None or a reason why doing a with tools VHD install on dut would be 
    futile"""
    if os_name in set(dom['name'] for dom in domlist):
        return "already have VM"
    with_tools_vhd = VHD_WITH_TOOLS_PATTERN % {'build':build, 'name': os_name,
                                               'encrypted':''}
    if not exists(with_tools_vhd):
        return "no VHD available"
    try:
        check_free(dut, target_os=os_name)
    except InsufficientStorage:
        return "insufficient storage for new VM"
    except InsufficientMemory:
        return "insufficient memory for new VM"

def install_guest(dut, guest='xp', kind='iso', busy_stop=False, 
                  encrypt_vhd=False, url=None):
    """Install guest on dut from media of type kind"""
    os_name, name = name_split(guest)
    print 'HEADLINE: installing', name, '('+os_name+')', 'on', dut, \
        'from', kind, 'BUSY_STOP' if busy_stop else 'STANDARD', \
        'ENCRYPTED' if encrypt_vhd else 'CLEAR'
    for already in list_vms(dut):
        if already['name'] == name_split(guest)[1]:
            if already['status'] == 'running':
                run(['xec-vm', '-u', already['uuid'], 'shutdown'], host=dut)
            run(['xec-vm', '-u', already['uuid'], 'delete'], host=dut)

    check_free(dut, target_os=guest)
    assert kind in ['iso', 'vhd', 'with_tools']
    print 'INSTALL_GUEST: ready to install', name
    do_guest_install(dut, kind, guest, encrypt_vhd, busy_stop=busy_stop,
                     url=url)
    print 'INSTALL_GUEST:', guest, 'installed on', dut
    return run(['xec-vm', '-n', name, 'get', 'uuid'], host = dut).strip()


#Not a perfect solution here but effective if mode is substituted for 'kind'
def entry_fn(dut, guest, encrypt_vhd, mode, url):
    if url == "":
        install_guest(dut, guest, mode, True, encrypt_vhd)
    else:
        install_guest(dut, guest, mode, True, encrypt_vhd, url)

def desc():
    return 'Install guest from iso or vhd.  If installing windows from a vhd, the vhd must be bvt-aware.'
