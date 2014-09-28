#!/usr/bin/python
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

import argparse, src.bvtlib.mongodb, pymongo, src.bvtlib.process_result, sys
from serverlib.tags import html_fragment, td, a, h1, h2, ol, li, tr, table, th
from pymongo import DESCENDING

def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(description="Create grid")
    parser.add_argument('-o', '--output-file',
                        default = None,
                        help = 'Set the output file')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help = 'Set verbosity flag')
    parser.add_argument('-m', '--max-results',
                        type = int, default = 128 * 256,
                        help = 'Maximum results to output')
    parser.add_argument('-b', '--branch',
                        default = 'master',
                        help = 'Branch to produce grid for')
    # parser.add_argument('match', nargs='*')

    args = parser.parse_args()

    if args.output_file is None:
        print 'Must specify an output file'
        sys.exit(1)

    mongo = src.bvtlib.mongodb.get_autotest()
    builds_query = {'branch': args.branch}
    results_by_build = {}
    results = []
    tests = set()
    build_ids = []

    for build in mongo.builds.find(builds_query, limit = args.max_results).sort([('tag_time', DESCENDING)]):
        build_id = build['_id']
        # print 'build id is', build_id
        # results_for_build = {'build': build_id}
        results_for_build = {}
        results_query={'build': build_id}
        interesting = False
        for result in mongo.results.find(results_query):
            if 'infrastructure_problem' not in result:
                # print '  got result', result
                if 'test_case' in result:
                    test_case = result['test_case']
                    if test_case is not None:
                        failure = result['failure'] if 'failure' in result else None
                        if failure is not None:
                            interesting = True
                            result = True if failure in ['', None] else failure
                            if test_case in results_for_build:
                                results_for_build[test_case].append(result)
                                # results_for_build[test_case] += 1
                            else:
                                results_for_build[test_case] = [ result ]
                                # results_for_build[test_case] = 1
        if interesting:
            results.append(results_for_build)
            results_by_build[build_id] = results_for_build
            build_ids.append(build_id)
        tests.update(results_for_build.keys())

    # build_ids = results_by_build.keys()
    # build_ids.sort()

    test_names = [ test for test in tests ]
    test_names.sort()

    column_number = 1
    column_numbers = {}
    column_names = [th['build']]
    column_keys = []
    test_labels = {}
    
    for test_name in test_names:
        test_label = test_name.replace(' ', '_')
        column_numbers[test_name] = column_number
        column_heading = th[a(href="#"+test_label, title=test_name)[repr(column_number)]]
        column_names.append(column_heading)
        column_keys.append(li[a(name=test_label)[a(href="http://autotest/results?reverse=1&test_case="+test_name)[test_name]]])
        test_labels[test_name] = test_label
        column_number += 1

    rows = [column_names]

    for build_id in build_ids:
        build_results = results_by_build[build_id]
        cells = [th[a(href="http://autotest/build/"+build_id)[build_id]]]
        for test in test_names:
            if test in build_results:
                fail_count = len(build_results[test])
                cells.append(td(bgcolor= "#ff8080" if fail_count == 1 else "#ff0000")[a(href="#"+test_labels[test], title=test)[repr(fail_count)]])
            else:
                cells.append(td['-'])
        row = [tr[cells]]
        rows.append(row)

    column_key = [ol[column_keys]]
    grid = [table(border='true')[rows]]

    outfile = open(args.output_file, 'wb')

    html = [ h1['BVT results grid for '+args.branch],
             h2['Column key'],
             column_key,
             h2['Results'],
             grid
             ]

    page = html_fragment(html)

    outfile.write(page)

    outfile.close()
    return

if __name__ == '__main__':
    main()

