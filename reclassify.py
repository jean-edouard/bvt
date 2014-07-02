#! /scratch/autotest_python/bin/python
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

from pprint import pprint
from bvtlib.mongodb import get_autotest, DESCENDING
from sys import stderr
from bvtlib.process_result import process_result
from time import asctime, localtime
MDB = get_autotest()
import argparse
from pymongo.objectid import ObjectId

results = 0
kinds = {}
query = {}
parser = argparse.ArgumentParser(description="Reclassify results")
parser.add_argument('indices', nargs='*',metavar='ID',
                     help='Specifically process ID')
parser.add_argument('-v', '--verbose', action='store_true',
                    help='Show actions')
args = parser.parse_args()
if args.indices:
    query['_id'] = {'$in': [ObjectId(x) for x in args.indices]}

N = 0
for result in MDB.results.find(query).sort([('start_time', DESCENDING)]):
    N += 1
    kind = process_result(result, MDB, verbose=args.verbose,
                          replace=True)
    kinds.setdefault(kind, 0)
    kinds[kind] += 1
    results += 1
    if results % 100 == 0:
        out = ''
        for kind in sorted(kinds.keys()):
            out += ' % s=%.3f%%' % (kind, 100.0*kinds[kind]/results)
        print >>stderr, 'coverage=%.3f%% %s %s\r' % (
            100.0*results / N, asctime(localtime(result['start_time'])), out)
        
