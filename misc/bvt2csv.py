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

"""CLI to create a CSV file of the results."""
import argparse, bvtlib.mongodb, pymongo, bvtlib.process_result, sys
import csv, re, itertools

LEGAL = ' abcdefghjijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_,'
def light_escape(string):
    """readable regexp escaping"""
    out = ''
    for char in string:
        if char not in LEGAL:
            out += '\\'
        out += char
    return out

def build_details(mongo, build_id):
    return mongo.builds.find_one({'_id': build_id})

def possibilities(mongo):
    """Return a cursor for recent failures result documents."""
    query = {'end_time': {'$exists':True},
             'build':{'$exists':True},
             'failure': {'$exists':True}}
    return mongo.results.find(query).sort([('end_time', pymongo.DESCENDING)])

def as_string(x):
    if isinstance(x, basestring):
        return x
    # if isinstance(x, dict):
    #     return None
    return repr(x)

def as_build(x):
    if isinstance(x, dict):
        if '_id' in x:
            x = x['_id']
        else:
            print 'no _id in build', x
            return None
    if isinstance(x, basestring):
        mob = re.search('([0-9]+)', x)
        if mob:
            return int(mob.group(1))
        return x
    return repr(x)

def matching_result(result, classifier):
    # print 'matching result', result, 'against classifier', classifier
    for key, value in classifier.iteritems():
        # print '  key =', key, 'value =', value
        if key is None:
            continue
        if key not in result:
            return False
        result_value = result[key]
        if value is None and result_value is None:
            continue
        if value is None or result_value is None:
            return False
        # print '  key =', key, 'result[key] =', result_value, 'type(result_value) =', type(result_value), 'value =', value
        result_value = as_string(result_value)
        if re.search(value, result_value):
            return True
    return False

def format_people(people_list):
    return ', '.join(people_list) if people_list is not None else ''

# from http://docs.python.org/2/library/itertools.html?highlight=itertools#recipes:
def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx
    args = [iter(iterable)] * n
    return itertools.izip_longest(fillvalue=fillvalue, *args)

def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(description="Create classifier record")
    parser.add_argument('-o', '--output-file',
                        default = None,
                        help = 'Set the output file')
    parser.add_argument('-l', '--list', action='store_true',
                        help = 'Show existing classifiers')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help = 'Set verbosity flag')
    parser.add_argument('-m', '--max-results',
                        type = int, default = 0,
                        help = 'Maximum results to output')
    parser.add_argument('-c', '--count',
                        action='store_true',
                        help = 'Output the count of matches')
    parser.add_argument('-b', '--builds',
                        action='store_true',
                        help = 'Output which builds match the classifier')
    parser.add_argument('-r', '--build-ranges',
                        action='store_true',
                        help = 'Output which builds match the classifier')
    parser.add_argument('-K', '--key',
                        default = None,
                        help = 'Arbitrary other search key')
    parser.add_argument('-V', '--value',
                        default = None,
                        help = 'Value for -K')
    parser.add_argument('-g', '--general',
                        action='store_true',
                        help = 'output general information table')
    parser.add_argument('-a', '--all-columns',
                        action='store_true',
                        help = 'output all columns seen in the results')
    parser.add_argument('match', nargs='*')
    columns = ['test_case','latest_build'] # always put these first
    for key in bvtlib.process_result.CLASSIFIER_FIELDS:
        # print 'adding key', key
        parser.add_argument('--'+key.replace('_', '-'), type=str,
                            metavar='VALUE', 
                            help='VALUE should occur in '+key+' string')
        if key not in columns:
            columns.append(key)
    args = parser.parse_args()
    if args.list:
        for key in bvtlib.process_result.CLASSIFIER_FIELDS:
            print '  --'+key.replace('-', '_')
        return
    mongo = bvtlib.mongodb.get_autotest()
    rows = []
    # print 'columns are', columns
    classifier = {}
    for key in bvtlib.process_result.CLASSIFIER_FIELDS:
        # print ' looking for classifiers: key', key
        field = bvtlib.process_result.field_name(key)
        value = getattr(args, key, None)
        if value:
            # print '  value', value
            classifier[field] = value

    if args.match != []:
        for pair in grouper(args.match, 2):
            classifier[pair[0]] = pair[1]

    if args.key is not None:
        if args.value is None:
            print 'If a key is specified, its value must be specified too.'
            return
        classifier[args.key] = args.value

    if classifier == {}:
        print 'ERROR: specifiy some constraints'
        sys.exit(1)

    general_tabular = not (args.builds or args.build_ranges)

    if args.output_file is None:
        print 'Must specify an output file'
        sys.exit(1)

    if args.builds or args.build_ranges:
        collecting_builds = True

    if collecting_builds:
        builds = {}
        build_names = {}
    else:
        builds = None

    # classifier['owner'] = True  # must be present, value is not used
    if args.verbose:
        print 'Searching for matches to', classifier
    countdown = args.max_results
    scanned = 0
    matches = 0
    first_build = sys.maxint
    last_build = 0
    for result in possibilities(mongo):
        scanned += 1
        if matching_result(result, classifier):
            matches += 1
            if general_tabular:
                for field, _ in result.iteritems():
                    if args.all_columns and field not in columns:
                        columns.append(field)
                rows.append(result)
            if collecting_builds:
                build_name = result['build'] if 'build' in result else 'unknown'
                build = as_build(build_name)
                build_names[build] = build_name
                if build < first_build:
                    first_build = build
                if build > last_build:
                    last_build = build
                builds[build] = builds[build] if build in builds else 1
            countdown -= 1
            if countdown == 0:
                break

    if args.verbose:
        print 'scanned', scanned, 'results, getting', matches, 'matches'

    if general_tabular or args.builds or args.build_ranges:
        outfile = open(args.output_file, 'wb')


    if general_tabular:
        writer = csv.DictWriter(outfile,
                                fieldnames=columns,
                                quoting = csv.QUOTE_NONNUMERIC,
                                extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    if args.build_ranges:
        writer = csv.writer(outfile,
                            quoting = csv.QUOTE_NONNUMERIC)
        writer.writerow(['start', 'end', 'start', 'end'])
        builds_affected = sorted(builds.keys())
        build = first_build
        range_start = first_build
        while build <= last_build:
            while build <= last_build:
                build += 1
                if build not in builds:
                    range_end = build - 1
                    row = [ range_start, range_end, build_names[range_start], build_names[range_end] ]
                    writer.writerow(row)
                    break
            while build <= last_build:
                build += 1
                if build in builds:
                    range_start = build
                    break

    if args.builds:
        writer = csv.writer(outfile,
                            quoting = csv.QUOTE_NONNUMERIC)
        writer.writerow(['build number', 'build name', 'count', 'branch', 'blame', 'commits'])
        for affected in sorted(builds.keys()):
            details = build_details(mongo, build_names[affected])
            tag_time = details['tag_time'] if 'tag_time' in details else None
            build_time = details['build_time'] if 'build_time' in details else None
            blame = details['blame'] if 'blame' in details else None
            commits = details['commits'] if 'commits' in details else None
            branch = details['branch'] if 'branch' in details else None
            people = format_people(blame).encode('utf_8')
            row = [affected, build_names[affected], builds[affected], branch, people]
            # row.append(commits)
            if commits is not None:
                for commit in commits:
                    for element in commit:
                        row.append(element)
            writer.writerow(row)

    if general_tabular or args.builds or args.build_ranges:
        outfile.close()

    if args.count:
        print matches

    return

if __name__ == '__main__':
    main()
