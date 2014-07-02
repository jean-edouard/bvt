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

"""Check that setup is correct for PXE booting"""
from bvtlib.dhcp import get_addresses
from bvtlib.run import islink, isdir, run
from bvtlib.settings import PXE_SERVER, PXE_DIR
from bvtlib.exceptions import ExternalFailure
from os.path import join

class PxeStuffMissing(ExternalFailure): 
    """The symlink structure is wrong"""

def verify_pxe_rig(dut):
    """Check that setup is correct on the PXE server for dut;
    throw PxeStuffMissing otherwse"""
    def fail(*why): 
        """throw PxeStuffMissing"""
        print 'PXE_INSTALL: problem', dut, why
        raise PxeStuffMissing('verifying PXE rig on', dut, 'failed', *why)
    dut_mac, dut_ip = get_addresses(dut)
    print 'PXE_INSTALL: verify', dut, 'MAC', dut_mac, 'IP', dut_ip
    dut_quad = dut_ip.split('.')
    dut_num_quad = [int(x) for x in dut_quad]
    dut_hex_quad = ''.join('%02x' % x for x in dut_num_quad).upper()
    print 'PXE_INSTALL:', dut, 'IP', dut_ip, 'hex quad', dut_hex_quad

    mac_fn = dut_mac.replace(':','-').lower()
    mac_dir = join(PXE_DIR, mac_fn)
    ip_dir = join(PXE_DIR, dut_hex_quad)
    target_pxe_cfg = join(mac_dir, 'pxelinux.cfg')
    dut_file = join(PXE_DIR, dut)
    print 'PXE_INSTALL: target config is', target_pxe_cfg, 'and dut file is', dut_file
    direct_pxe_cfg = join(PXE_DIR, 'pxelinux.cfg', dut_hex_quad)
    if not isdir(mac_dir, host=PXE_SERVER):  
        fail('directory', mac_dir, 'not found')
    for alias, want in [
        (ip_dir,mac_fn),
        (dut_file,mac_fn),
        (target_pxe_cfg,'../autotest/'+dut+'.cfg')]:
        print 'PXE_INSTALL: verifying', alias, 'against', want
        if not islink(alias, host=PXE_SERVER):
            command = 'sudo ln -s %s %s' % (want, alias)
            print 'HINT:'
            print '  ', command
            fail('symlink missing; create with: ln -s %s %s' % (want, alias))
        
        target = ' '.join((run(['readlink', alias], split=True, 
                               host=PXE_SERVER))[0])
        if want != target:
            fail('symlink', alias, 'should point to', want,
                 'but points to', target)
    if not islink(direct_pxe_cfg, host=PXE_SERVER):
        fail('symlink missing; create with ln -s ../%s/pxelinux.cfg %s' % (
                dut_hex_quad, direct_pxe_cfg))
    else: 
        print 'PXE_INSTALL: already have', direct_pxe_cfg
    print 'PXE_INSTALL: verified PXE rig of', dut
