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

from bvtlib import mongodb, text_table
import optparse, time, sys, socket, pymongo.objectid
from pymongo import DESCENDING, ASCENDING

def show_line(line, options, base_time):
    text = line['message']
    seq = []
    while text.startswith(' '): 
        text = text[1:]
    if options.timestamps: 
        seq.append(time.asctime(time.localtime(line['time'])))
    if options.delta: 
        seq.append('%.3f' % (line['time'] - base_time))
    if len(options.kind ) != 1: 
        seq.append(line['kind'])
    if options.eliminate_substrings:
        for sstr in options.substring:
            text = text.replace(sstr, '')
    seq.append(text)
    return seq

def show_lines(db, central, before, after, options, covered, base_time, 
               result_id):
    lines = []
    if before:
        cur = db.logs.find({'result_id':result_id,
                            'time' : {'$lt': central}}
                           ).sort('time',DESCENDING).limit(before) 
        if before or after: 
            print
        for row in reversed(list(cur)):
            lines.append(show_line(row, options, base_time))
    ncovered = central['time']
    lines.append(show_line(central, options, base_time))
    if after:
        cur2 = db.logs.find({'result_id':result_id,
                            'time' : {'$gt': central}}
                           ).sort('$natural',ASCENDING).limit(after)
        latest = None
        for row in cur2:
            lines.append(show_line(row, options, base_time))
            ncovered = row['time']
            latest = row['time']
    return ncovered, lines

def main():
    parser = optparse.OptionParser(
        'usage: cat_log [options] result_guid [result_guid...]\n'
        '\n'
        '\n  autotest_number values can be obtained from find_log or the\n'
        'web interface.\n')
    parser.add_option('-k', '--kind', metavar = 'KIND', action='append', 
                      default=[],
                      help = 'Show log entries with class substring KIND '
                      '(case insensitve)')
    parser.add_option('-a', '--all', action='store_true',
                      help = 'Show log entries with all classes '
                      '(implicit if -k unused)')
    parser.add_option('-s', '--substring', action='append', metavar='SUBSTRING',
                      help = 'Show log entries containing SUBSTRING')
    parser.add_option('-e', '--eliminate-substrings', action='store_true',
                      help= ' Eliminate substrings specified by --substring '
                      'from the output')
    parser.add_option('-t', '--timestamps', action='store_true',
                      help = 'Show timestamps')
    parser.add_option('-d', '--delta', action='store_true',
                      help = 'Show time deltas')
    parser.add_option('-A', '--after', action='store', metavar='N',
                      help = 'Show N lines after each matching line')
    parser.add_option('-B', '--before', action='store', metavar='N',
                      help = 'Show N lines before each matching line')
    parser.add_option('-F', '--format', action='store_true',
                      help = 'Tabulate output (involves two passes)')
    parser.add_option('-f', '--follow', action='store_true',
                      help = 'Follow mode; wait for new output')
    parser.add_option('-n', '--lines', action='store', metavar='N',
                      help = 'Show only the last N lines of output') 
    parser.add_option('--summary', action='store_true',
                      help = 'Show only HEADLINES, INFO and RESULTS if '
                      'no kinds are specified, and show deltas '
                      '(implied by '
                      'running this program with a name containing '
                      'the text "summary")')
    options,args = parser.parse_args()
    if len(args) == 0: 
        parser.error('supply at least one autotest_number')
    before = int(options.before) if options.before else 0
    after = int(options.after) if options.after else 0

    if options.summary or 'summary' in sys.argv[0]:
        options.delta = True
        options.format = True
        if options.kind == []:
            options.kind = ['HEADLINE', 'INFO', 'RESULT']
    if options.all or options.kind == []:
        kindf = []
    else:
        kindf = ['(' +' OR '.join( "kind LIKE '%%%s%%'" % (kind.upper()) for 
                                   kind in options.kind)+')']
    if options.substring:
        kindf.append ( '(' +' OR '.join( "message LIKE '%s'" % ('%'+subs+'%') 
                                         for subs in options.substring)+')')
    db = mongodb.get_autotest()
    db.logs.ensure_index([('result_id',ASCENDING)])
    acc = []
    latest_shown = {}
    errors = 0
    while True:
        for arg in args:
            result_doc = db.results.find_one({'_id':pymongo.objectid.ObjectId(arg)})
            if result_doc is None:
                print 'ERROR: could not find result',arg
                errors += 1
                continue
            result_id = result_doc['_id']
            covered = 0
            lshown = latest_shown.get(arg, 0)
            kindf2 = kindf + ['time>' + str(lshown)]
            spec = { 'result_id':result_id }
            if options.kind: 
                spec['kind'] = {'$in' : options.kind}
            cursor = db.logs.find(spec, max_scan=1000000)
            if options.lines: 
                cursor2 = cursor.limit(options.lines)
            else: 
                cursor2 = cursor.limit(100000)
            results = list(cursor2)
            if options.lines: 
                results.reverse()
            base_time = min( row['time'] for row in results) if results else 0
            for row in results:
                covered, lines = show_lines(db, row, before, after, options, 
                                            covered, base_time, result_id)
                latest_shown[arg] = max(latest_shown.get(arg, 0), row['time'])
                if not options.format:
                    for line in lines:
                        print ' '.join(line)
                else: acc += lines
        if not options.follow: break
        time.sleep(1)
    text_table.text_table(acc)
    sys.exit(errors)

if __name__ == '__main__': main()

