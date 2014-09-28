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

"""Connect to various DHCP servers"""
from src.bvtlib.settings import DHCP_SERVERS, USE_STATEDB_FOR_DHCP, USE_MONGO_FOR_MAC
from src.bvtlib.mongodb import get_autotest
from src.bvtlib.database_cursor import open_state_db, NoRows, open_config_db
from src.bvtlib.run import specify, isdir, run, isfile

class NoDHCPLease(Exception):
    """No DHCP Lease found"""
    pass

class SiteSupportUnimplemented(Exception): 
    """Site support not available"""
    pass

def dhcp_leases(timeout=10):
    """Return (MAC, IP, allocation time in text) for all leases
    on site"""
    if USE_STATEDB_FOR_DHCP:
        cdb = open_config_db()
        return [ (row['hardware'].upper(), row['ip'], 'static', 
                  row['reverse_dns'].split('.')[0]) for row in 
                 cdb.select('reverse_dns, hardware, ip FROM ips WHERE hardware NOTNULL')]
    ipaddress = None
    start = None
    name = None
    out = []
    for dhcp_server in DHCP_SERVERS:
        srun = specify(split=True, host=dhcp_server, timeout=timeout)
        for directory in ['/var/lib/dhcp3', '/var/lib/dhcp']:
            if not isdir(directory, host=dhcp_server):
                #print 'No', directory, 'on', dhcp_server  #commenting out since it  prints unnecessary logs during reboots and installations
                continue
            for spl in srun(['cat', directory+'/dhcpd.leases']):
                if len(spl) == 0: 
                    continue
                if spl[0] == 'lease': 
                    ipaddress = spl[1]
                    start = name = None
                if spl[0] == 'starts': 
                    start = ' '.join(spl[2 : 4])[:-1]
                if spl[0] == 'client-hostname':
                    name = spl[-1][1:-2] 
                if spl[0] == 'hardware':
                    mac = spl[2][:-1]
                if spl == ['}']:
                    out.append( (mac.upper(), ipaddress, start, name))
        for directory in ['/etc/dhcp3', '/etc/dhcp']:
            if isdir(directory, host=dhcp_server):
                if isfile(directory+'/dhcpd.conf', host=dhcp_server):
                    for spl in srun(['cat', directory+'/dhcpd.conf']):
                        if len(spl) == 3 and spl[0] == 'host' and spl[2] == '}':
                            name = mac = ipaddress = None
                        if spl[:2] == ['hardware', 'ethernet']:
                            mac = spl[-1][:-1]
                        if len(spl) == 2 and spl[0] == 'fixed-address':
                            ipaddress = spl[-1][:-1]
                        if len(spl) == 3 and spl[:2] == ['option', 'host-name']:
                            name = spl[-1][1:-2]
                        if spl == ['}'] and name and mac and ipaddress:
                            out.append ( (mac.upper(), ipaddress, 'static', name))
    return out

def get_addresses(host, timeout=10, description=None):
    """Return MAC and IP address of host"""
    if USE_MONGO_FOR_MAC:
        mdb = get_autotest()
        dut_doc = mdb.duts.find_one({'name':host})
        if dut_doc and dut_doc.get('mac-amt'):
            mac = dut_doc['mac-amt']
        elif dut_doc and dut_doc.get('mac'):
            mac = dut_doc['mac']
        else:
            mac = None
        return mac
    if USE_STATEDB_FOR_DHCP:
        ip = run(['host', host], split=True)[0][-1]
        cdb = open_state_db()
        try:
            mac = cdb.select1_field('mac', 'ips', ip=ip)
        except NoRows:
            print 'DHCP: no record for IP address', ip, 'in statedb'
        else:
            if mac:
                print 'DHCP: found', mac, 'for IP', ip, host, 'using statedb'
                return mac, ip
    else:
        for mac, ipa, _, name in dhcp_leases(timeout=timeout):
            if name and name.split('.')[0] == host.split('.')[0]: 
                return mac, ipa
    raise NoDHCPLease(host, description)

def canonical_mac(x):
    """Return canonical form of MAC address x"""
    return x.replace('-', ':').lower()

def mac_to_ip_address(mac_address, timeout=10, description=None):
    """Return IP address for mac_address of host"""    
    mac_address = canonical_mac(mac_address)
    if USE_STATEDB_FOR_DHCP:
        cdb = open_state_db()
        try:
            ip = cdb.select1_field('ip', 'ips', mac=mac_address, state=True)
        except NoRows:
            print 'DHCP: no IP for mac address', mac_address, 'in statedb'
        else:
            if ip:
                print 'DHCP: found', ip, 'for', mac_address
                return ip
    else:
        for mac, ipa, _, _ in dhcp_leases(timeout=timeout):
            if canonical_mac(mac) == mac_address:
                return ipa
    raise NoDHCPLease(mac_address, description)
    
