#
# Copyright (c) 2012 Citrix Systems, Inc.
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

"""Check that MAC addresses match between eth0 and brbridged"""
from src.bvtlib.run import run
from src.bvtlib.domains import list_vms

class MacAddressesMismatch(Exception):
    """eth0 and brbridged addresses do not match"""

def check_mac_addresses(dut):
    """Check that MAC address match"""
    addresses = {}

    # if we have an ndvm, this test needs to operate on the ndvm:
    ndvms = [x for x in list_vms(dut) if x['name'] in ['ndvm', 'Network']]
    if len(ndvms) == 1:
        prefix = ['sshv4v', '-o', 'StrictHostKeyChecking=no', '1.0.0.%d' % int(ndvms[0]['dom_id'])]
    elif len(ndvms) > 1:
        raise RuntimeError, "Test doesn't support multiple NDVMs"
    else:
        prefix = []

    for name in ['eth0', 'brbridged']:
        addresses[name] = run(prefix + [
                'cat', '/sys/class/net/'+name+'/address'], host=dut, 
                              word_split=True)
    print 'HEADLINE: platform interface adddresses', addresses
    if addresses['eth0'] != addresses['brbridged']:
        raise MacAddressesMismatch(addresses, dut)
   
def entry_fn(dut):
    check_mac_addresses(dut)

def desc():
    return 'Check that eth0 and brbridged'
