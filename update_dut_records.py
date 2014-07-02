#! /scratch/autotest_python/bin/python
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

from bvtlib.dhcp import dhcp_leases
from bvtlib.settings import ASSETS_BY_MAC, MAC_LINKS
from bvtlib.mongodb import get_autotest
from os import readlink
from re import match, search
from pprint import pprint

def update_dut_records(verbose=False):
    """Contact DHCP servers"""
    print 'UPDATE_DUT_RECORDS: starting'

    mdb = get_autotest()
    duts = mdb.duts.find()
    dutmap = dict([ (dut['name'],  dut) for dut in duts if 'name' in dut])
    leases = dhcp_leases()
    print 'UPDATE_DUT_RECORDS: considering', len(leases), 'leases'
    for (mac, _, _, name) in dhcp_leases():
        def read(path, lsplit=True):
            """read path with in assets system"""
            filename = ASSETS_BY_MAC % (mac.upper(), path)
            content = file(filename, 'r').readlines()
            if not lsplit:
                return content
            return [line.split() for line in content]
        lname = name.split('.')[0] if name else None
        if lname not in dutmap:
            continue 
        updates = {'mac_address' : mac.upper(), 'name' : lname}
        try:
            symlink = readlink(MAC_LINKS+'/'+mac)
        except OSError:
            pass
        else:
            asset_id = symlink.split('/')[-1]
            if match('[0-9a-f]{8}', asset_id):
                updates['asset_id'] = asset_id
        if 'development_mode' not in dutmap[lname]:
            updates['development_mode'] = 0
        try:
            lshw = read('lshw/lshw.txt')
        except IOError: 
            pass
        else:
            updates['model'] = ' '.join(lshw[2][1:])
            updates['make'] = ' '.join(lshw[3][1:])
        try:
            lspci = read('lspci/lspci.txt', lsplit=False)
        except IOError:
            pass
        else:
            for line in lspci:
                if line.startswith('00:02.0'):
                    m = search(r'\[([0-9a-f]{4}):(([0-9a-f]{4}))', line)
                    if m:
                        vid, pid = m.group(1), m.group(2)
                        platform = None
                        if vid == '8086':
                            if pid == '0126':
                                platform = 'Huron River'
                            if pid == '0046':
                                platform = 'Calpella'
                            if pid == '2a42':
                                platform = 'Montevina'
                        if platform:
                            updates['platform' ] = platform
                        else:
                            print 'ERROR:', lname, 'unrecognised', vid, pid
                    else:
                        print 'ERROR:', lname, 'could not find VID/PID'
        try:
            meminfo = read('meminfo/meminfo.txt')
        except IOError:
            pass
        else:
            updates['memory'] = int(meminfo[0][1]) * 1024
        if verbose:
            print 'for', lname, 'set', updates
        mdb.duts.update({'name':lname}, {'$set':updates})

    dutdocs = list(mdb.duts.find())
    print 'UPDATE_DUT_RECORDS: considering', len(dutdocs), 'docs'

    for dutdoc in dutdocs:
        if 'asset_id' not in dutdoc:
            if verbose:
                print 'no asset ID for', dutdoc['name'], dutdoc['_id']
            continue
        if dutdoc['asset_id'] == dutdoc['_id']:
            if verbose:
                print 'asset ID correct for', dutdoc['name'], dutdoc['asset_id']
            continue
        results = mdb.results.find({'dut':dutdoc['_id']}).count()
        print 'WARNING: should migrate', dutdoc['name'], 'to asset ID', \
            dutdoc['asset_id'], 'and', results, 'results'
        if mdb.duts.find_one({'_id': dutdoc['asset_id']}) is None:
            dutdocid = dict(dutdoc, _id = dutdoc['asset_id'])
            mdb.duts.save(dutdocid)
            print 'created dut record by ID'
        mdb.duts.remove({'_id': dutdoc['_id']})
        mdb.results.update({'dut': dutdoc['_id']},
                           {'$set': {'dut': dutdoc['asset_id'],
                                     'dut_name' : dutdoc['name']}},
                           multi=True)

if __name__ == '__main__': 
    update_dut_records(verbose=False)

