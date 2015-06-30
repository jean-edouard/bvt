#! /scratch/autotest_python/bin/python
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

from os.path import expanduser, exists
from sqlalchemy import create_engine, MetaData, Table, select, insert
from bvtlib.settings import DATABASE_CREDENTIALS    
from sys import argv

password = DATABASE_CREDENTIALS['configdb']['pwd']
host = DATABASE_CREDENTIALS['configdb']['host']
engine = create_engine(
    'postgresql://configdb:'+password+'@'+host)
conn = engine.connect()

print 'connected'
meta = MetaData()
ips = Table('ips', meta, autoload=True, autoload_with=engine)

def ip_address_generator():
    for base in ['10.80.249.%d', '10.80.248.%d']:
        for x in range(1, 256):
            yield base % (x,)

spare = []
for candidate in ip_address_generator():
    q = select([ips]).where(ips.c.ip == candidate)             
    if list(conn.execute(q)) == []:
        spare.append(candidate)
        break

if spare == []:
    print 'ERROR: no spare addresses'
    exit(1)

if len(argv) < 3:
    print 'a spare IP address is', spare[0]
    exit(0)

hostname = argv[1]
if not hostname.endswith('.xci-test.com'):
    print 'ERROR: invalid FQDN', hostname
    exit(3)

mac = argv[2].lower()
if len(mac.split(':')) != 6:
    print 'ERROR: invalid MAC', mac
    exit(2)

for row in conn.execute(select([ips]).where(ips.c.hardware==mac)):
    if row['reverse_dns'] == hostname:
        print 'INFO: already have', row
        exit(0)
    else:
        print 'ERROR: already have MAC address', mac, 'in', row
        exit(4)

for row in conn.execute(select([ips]).where(ips.c.reverse_dns == hostname)):
    print 'ERROR: already have host', hostname, 'in', row
    exit(5)

args = {'ip':spare[0], 'service':'internal',
        'reverse_dns_type':'PTR',
        'reverse_dns' : hostname,
        'hardware' : argv[2],
        'boot_protocol':'pxe'}
inscmd = ips.insert().values(**args)
print str(inscmd), args

go = raw_input('type go>')
print 'you typed %r' % (go)
if go == 'go':
    conn.execute(inscmd)

print 'done insert'
