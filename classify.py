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

"""CLI to create classifier record which in turn create whiteboard entries """
import argparse, bvtlib.mongodb, pymongo, bvtlib.process_result, sys
import pprint, pwd, getpass
from time import localtime, asctime 
LEGAL = ' abcdefghjijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_,'
def light_escape(string):
    """readable regexp escaping"""
    out = ''
    for char in string:
        if char not in LEGAL:
            out += '\\'
        out += char
    return out

def unknown_failures(mongo, null_whiteboard=False):
    """return a cursor for recent unknown failures result documents"""
    query = {'end_time': {'$exists':True}, 'build':{'$exists':True},
             'failure': {'$exists':True, '$ne': ''},
             'whiteboard': ''}
    if null_whiteboard:
        query= {'$or': [dict(query, whiteboard = ''), 
                        dict(query, whiteboard={'$exists': False})]}
    return mongo.results.find(query).sort([('end_time', pymongo.DESCENDING)])

def list_recent_unclassified(mongo, limit=10):
    """show recent unclassified results as classify commands"""
    for result in unknown_failures(mongo).limit(limit):
        fstr = result['failure'].replace('internal BVT bug: ', '')
        fregexp = light_escape(fstr)
        if len (fregexp) > 100:
            fregexp = fregexp[:50]+'.*'+fregexp[-50:]
        cmd = ''
        for key in bvtlib.process_result.CLASSIFIER_FIELDS:
            value = result.get(key)
            if value:
                if len(value) > 100:
                    value = value[:50] +'.*'+value[50:]
                value = light_escape(value)
                cmd += ' --'+key.replace('_', '-')
                if ' ' in value:
                    cmd += " '"+value+"'"
                else:
                    cmd += " "+value
                
        print 'classify '+cmd
        print

def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(description="Create classifier record")
    parser.add_argument(
        'word', metavar='WORD', type=str, nargs='*',
        help='A word of the whiteboard message')
    parser.add_argument('-l', '--list', action='store_true',
                        help = 'Show existing classifiers')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help = 'Set verbosity flag')
    for key in bvtlib.process_result.CLASSIFIER_FIELDS:
        parser.add_argument('--'+key.replace('_', '-'), type=str,
                            metavar='VALUE', 
                            help='VALUE should occur in '+key+' string')
    args = parser.parse_args()
    mongo = bvtlib.mongodb.get_autotest()
    if args.list:
        for doc in mongo.classifiers.find():
            cmd = ''
            for key in bvtlib.process_result.CLASSIFIER_FIELDS + ['earliest_build']:
                field = bvtlib.process_result.field_name(key)
                arg = '--'+key.replace('-', '_')
                if doc.get(field):
                    cmd += ' %s %s' % (arg, ("'"+doc[field]+"'") if ' ' in 
                                         doc[field] else doc[field] )
            print 'classify'+ cmd, '"'+doc.get(
                'whiteboard', '')+'"', '#', doc['_id']
        print 
        return
    whiteboard = ' '.join(args.word)
    classifier = {}
    for key in bvtlib.process_result.CLASSIFIER_FIELDS:
        field = bvtlib.process_result.field_name(key)
        value = getattr(args, key, None)
        if value:
            classifier[field] = value
    if (not whiteboard and classifier == {}):
        print
        print 'Some example invocations:'
        print
        list_recent_unclassified(mongo)
        return
    if classifier == {}:
        print 'ERROR: specifiy some constraints'
        sys.exit(1)
    if whiteboard == '':
        print 'Searching for matches to', classifier
        classifier['owner'] = getpass.getuser()
        count = 0
        tot = 0
        for result in unknown_failures(mongo):
            tot += 1
            if bvtlib.process_result.check_classifier(
                mongo, classifier, result, verbose=args.verbose):
                pprint.pprint(result)
                count += 1
                if count> 10:
                    break
        print 'scanned', tot, 'results'
        return
    print 'whiteboard message:', whiteboard
    print 'classifier', classifier
    already = mongo.classifiers.find_one(classifier)
    if already:
        classifier['_id'] = already['_id']
        print 'Reusing ID', already['_id']
    classifier['whiteboard'] = whiteboard
    classifier['owner'] = getpass.getuser()
    print 'saving classifier', classifier
    mongo.classifiers.save(classifier)
    print 'scanning unknown failures'
    count = 0
    codes = {}
    for result in unknown_failures(mongo, null_whiteboard=False):
        code = bvtlib.process_result.process_result(result, verbose=False, 
                                                    mongo=mongo)
        codes.setdefault(code, 0)
        codes[code] += 1
        count += 1
        if count % 100 == 0:
            print codes, count, asctime(localtime(result['end_time']))

if __name__ == '__main__':
    main()
