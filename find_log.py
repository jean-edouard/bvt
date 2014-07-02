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

from bvtlib import database_cursor, text_table, mongodb
import optparse, sqlite3, time, datetime, sys

def strip_tz(x):
    offset = x.utcoffset()
    if offset is not None: return x.replace(tzinfo=None) - offset
    else: return x

def main():
    parser = optparse.OptionParser(
        'find_log [options]\n\nfinds autotest_number values for recent tests\n')
    parser.add_option('-b', '--build', action='store_true',
                      help = 'Show build name')
    parser.add_option('-s', '--status', action='store_true',
                      help = 'Show status field')
    parser.add_option('-m', '--machine', action='store_true',
                      help = 'Show machine field')
    parser.add_option('--model', action='store_true',
                      help = 'Show model field')
    parser.add_option('-t', '--timestamps', action='store_true',
                      help = 'Show start time of tests')
    parser.add_option('-c', '--test-case', action='store_true',
                      help = 'Show test case')
    parser.add_option('-F', '--failure-regexp', action='store',
                      default = [], metavar='REGEXP',
                      help = 'Show cases where failure contains REGEXP')
    parser.add_option('-M', '--machine-name', action='append',
                      default = [], metavar='DUT',
                      help = 'Show cases on DUT')
    parser.add_option('-N', '--negative', action='store_true',
                      help = 'Show only tests that failed')
    parser.add_option('-U', '--uninvestigated', action='store_true',
                      help = 'Show only uninvestigated failures, i.e. '
                      'where there is no whiteboard entry')
    parser.add_option('-C', '--test-case-regexp',action='store',default=[],
                      help = 'Show only tests where test cases matches REGEXP',
                      metavar='REGEXP')
    parser.add_option('-S', '--log-regexp', action='store', default=[],
                      help = 'Show only tests with log entries '
                      ' where REGEXP can be found',
                      metavar='REGEXP')
    parser.add_option('-L', '--limit', action='store',  metavar='N',
                      default=20,
                      help = 'Show at most N tests (default 20)')
    parser.add_option('-u', '--unformatted-output',
                      action='store_true', help='Disable formatting')
    options, args = parser.parse_args()
    query = {'test_case': {'$exists':True}}
    if options.uninvestigated:
        query['whiteboard'] = {'$exists':True}
    if options.negative or options.uninvestigated:
        query['failure'] = {'$exists':True}
    if options.failure_regexp:
        query['failure'] = {'$regex': options.failure_regexp}
    if options.test_case_regexp:
        query['test_case'] = {'$regex': options.failure_regexp}
    if options.machine_name:
        query['dut'] = {'$in': options.machine_name }
    i = 0
    lines = []
    mdb = mongodb.get_autotest()
    try:
        for row in mdb.results.find(query, sort=[('start_time', mongodb.DESCENDING)],
                                    limit=int(options.limit)):
            if options.log_regexp:
                if mdb.logs.find_one( { 'result_id':row['_id'], 
                                 'message': {'$regex': options.log_regexp}}) is None:
                    continue
            line = []
            line.append(str(row['_id']))
            if options.timestamps: 
                line.append( time.asctime(time.localtime(row['start_time'])))
            if options.machine: line.append( row.get('dut') or '[unknown dut]')
            if options.model: line.append( row.get('model'))
            if options.test_case: 
                line.append( row['test_case'] or  '[unknown case]')
            if options.build: line.append( row['build'] or '[unknown buid]')
            f = row.get('failure')
            if options.status:  
                if row.get('end_time') and not f: line.append('PASS')
                elif f: line.append('FAILED %r ' % f)
                else: line.append('RUNNING')
            i += 1
            if options.unformatted_output:
                print ' '.join(str(x) for x in line)
            else: lines.append(line)
            if len(line) == 1: print line[0]
            if options.limit != '-' and i == int(options.limit): break
    except IOError, e:
        print 'IO error',e
        if 'Broken pipe' in repr(e): return
        else: raise
    if lines and len(lines[0]) > 1: text_table.text_table(lines)
if __name__ == '__main__': main()

