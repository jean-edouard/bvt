#
# Copyright (c) 2011 Citrix Systems, Inc.
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

"""Run vhdcompact"""
from bvtlib import  exceptions
from bvtlib.wait_to_come_up import wait_to_come_up
from bvtlib.wait_for_windows import wait_for_windows, is_windows_up
from bvtlib.run import specify
from bvtlib.archive_vhd import archive_vhd
from os import unlink
import re
from os.path import split, basename

class UnexpectedVHDCompactOutput(exceptions.ExternalFailure): 
    """Unexpected content"""

class UnableToConnectAfterVHDCompact(exceptions.ExternalFailure): 
    """Trashed VM"""

class UnimplementedOperation(Exception):
    """Fix me"""

class WindowsStillUp(Exception):
    """Windows still up when told to go down"""

class CannotArchiveVHD(Exception):
    """Cannot archive VHD file"""

def vhdcompact_reboot(dut, guest, operation='pipe'):
    """Run vhdcmpact on dut for guest then reboot"""
    wait_to_come_up(dut)
    print 'VHDCOMPACT: connected to dut', dut, 'for', operation 
    go = specify(host=dut)
    vm_address = wait_for_windows(dut, guest)
    go(['xec-vm', '-n', guest, 'shutdown'], timeout=600)
    print 'VHDCOMPACT:', 'shut down domain', guest 
    if is_windows_up(vm_address):
        raise WindowsStillUp(dut, guest)
    result = 'vhdcompact not run'
    before = archive_vhd(dut, guest, artifact_name = 'before-vhdcompact', 
                         have_tools=False, publish=False)
    if before is None:
        raise CannotArchiveVHD(dut, guest)
    found =  False
    disk = 0
    while 1:
        physical_path, stderr_log, exit_code = go(
            ['xec-vm', '-n', guest, '--disk', 
             str(disk), 'get', 'phys-path'], stderr=True, 
            ignore_failure=True)
        print 'VHDCOMPACT: physical path', physical_path, 'for', disk
        if exit_code != 0: 
            assert 'does not exist' in stderr_log, (exit_code, stderr_log)
            break
        
        if physical_path.startswith('/storage/disks'):
            found = True
            break
        disk += 1

    assert ' ' not in physical_path
    pathe = physical_path.split()[0]
    if operation == 'inplace':
        print 'VHDCOMPACT:', 'found disk on ID', disk, \
            'path', pathe 
        out = go(['vhdcompact', pathe], timeout=1800)
        if 'Already compacted' in out:
            result = 'already compacted'
        else:
            match = re.search(
                r'Size before\s+([0-9]+)\s+MB.\s+'+
                r'Size after\s+([0-9]+)\s+MB.'+
                r'\s+Reclaimed\s+([0-9]+)\s+MB', out)
            if match is None:
                raise UnexpectedVHDCompactOutput(out)
            result = 'compacted from %sMB to %sMB' % (
                match.group(1), match.group(2))
        print 'VHDCOMPACT:', 'disk on ID', disk, 'path', \
            pathe, result 
    elif operation == 'pipe':
        base = basename(split(pathe)[1])+'.sync'
        devname = '/dev/mapper/'+base

        go(['vhd-dm-create', '--readonly', '--partitions',
             '--device-name', base, pathe])
        try:
            go(['vhdcompact', '-c', '-p', '-r', '-m4', 
                '-b', devname, pathe, '>', pathe+'.new'],
                timeout=3600, shell=True)
        finally:
            go(['vhd-dm-remove', '--partitions', base])
        sizes = [int(go(['stat', '-c', '%s', pathe+postfix], 
                                 split=True)[0][0])
                 for postfix in ['', '.new']]
        result = 'size went from %d to %d (%d%%)' % (
            sizes[0], sizes[1], 
            (100.0*(sizes[0] - sizes[1]) / sizes[0] if 
             sizes[0] else 0))

        go(['mv', '-f', pathe, pathe+'.old'])
        go(['mv', pathe+'.new', pathe])
    elif operation == 'noop':
        pass
    else:
        raise UnimplementedOperation(operation)
    after = archive_vhd(dut, guest, artifact_name='after-vhdcompact', 
                        have_tools=False, publish=False)
    if after is None:
        raise CannotArchiveVHD(dut, guest)
    for command in ['start', 'switch']:
        go(['xec-vm', '-n', guest, command], timeout=600)

    try:
        wait_for_windows(dut, guest, timeout=600)
    except Exception, exc:
        print 'HEADLINE: vhdcompcat made VHD copy', before, 'into unbootable VHD copy', after
        raise  UnableToConnectAfterVHDCompact(exc)
    else:
        print 'VHDCOMPACT: deleting VMs since vhdcompact worked'
        unlink(before)
        unlink(after)
    print 'VHDCOMPACT:', 'connected to Windows guest', guest 
    print 'HEADLINE:', guest, result 


# NOTE: this is a generator
def make_test_cases():
    """Produce test cases in various combinations"""
    for des, flag, options in [
        ('', 'noop', ['--windows-reboot']),
        # (', run vhdcompact on it', 'inplace', 
        #  [ '--vhdcompact-in-place-reboot']),
        (', pipe it through vhdcompact', 'pipe', 
         ['--vhdcompact-pipe-reboot']),
        ]:
        yield {'description' : 'Shutdown $(OS_NAME)' + des +
               ' then make sure it still boots', 'trigger': 'VM ready',
               'bvt':False,
               'command_line_options' : options,
               'function' : vhdcompact_reboot,
               'arguments' : [('dut', '$(DUT)'), ('guest', '$(GUEST)'),
                              ('operation',flag)]}
