#! /scratch/autotest_python/bin/python
#
# Copyright (c) 2014 Citrix Systems, Inc.
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

import sys
print "path is", sys.path
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core.context_processors import csrf
from serverlib import constraints
import argparse, bvtlib.mongodb, pymongo, bvtlib.process_result, sys
import nevow.flat
from nevow.tags import hr, td, a, h1, h2, ol, li, tr, table, th, div, title, p, br, form, input as stan_input, option, select
from pymongo import ASCENDING, DESCENDING
from time import asctime, gmtime, strftime, clock
from re import compile, IGNORECASE
from operator import itemgetter

def rgb_string(r, g, b, intensity=1.0):
    total = max(r, g, b)
    def adjust(x, tot, inten):
        base = 1.0 - float(inten)
        return (base + ((float(x) / tot) * float(inten))) * 255
    return '#%02x%02x%02x' % (adjust(r, total, intensity),
                              adjust(g, total, intensity),
                              adjust(b, total, intensity))

white = "white"
amber = rgb_string(.5, .5, 0, .5)
red = rgb_string(1, 0, 0, .5)
pale_red = rgb_string(1, 0, 0, .25)
green = rgb_string(0, 1, 0, .5)
pale_green = rgb_string(0, 1, 0, .25)

key_text = 'Each cell show successes (on the left) then failures (on the right).  The hover text for each cell shows more detail of the fails.'

key_table = [table(border='true', style="border-collapse: collapse")[
             [tr[th(bgcolor=green)['Tests with several passes and no fails are shown like this.']]],
             [tr[th(bgcolor=pale_green)['Tests with one pass and no fails are shown like this.']]],
             [tr[th(bgcolor=amber)['Tests with both passes and fails are shown like this.']]],
             [tr[th(bgcolor=pale_red)['Tests with one fail and no passes are shown like this.']]],
             [tr[th(bgcolor=red)['Tests with several fails and no passes are shown like this.']]]]]

proportionate_colour = True

def testXbuild_grid(argsdict, request=None):
    start_time = clock()
    one_week = 60 * 60 * 24 * 7
    one_week_ago = start_time - one_week

    max_results = (int(argsdict['max_results'])
                   if ('max_results' in argsdict and argsdict['max_results'] != '')
                   else 128)
    if max_results < 1:
        print 'Max results must be at least 1'
        sys.exit(1)

    countdown = max_results

    test_cases = (None if ('test_cases' not in argsdict
                           or argsdict['test_cases'] == None
                           or argsdict['test_cases'] == '')
                  else (compile(argsdict['test_cases']) if ('case' in argsdict and argsdict['case'])
                        else compile(argsdict['test_cases'], IGNORECASE)))

    exclude_cases = (None if ('exclude_cases' not in argsdict
                              or argsdict['exclude_cases'] == None
                              or argsdict['exclude_cases'] == '')
                     else (compile(argsdict['exclude_cases']) if ('case' in argsdict and argsdict['case'])
                           else compile(argsdict['exclude_cases'], IGNORECASE)))

    results_by_build = {}
    results = []
    tests = set()
    build_ids = []

    mongo = bvtlib.mongodb.get_autotest()
    branch = argsdict['branch'] if 'branch' in argsdict else 'master'
    builds_query = {'branch': branch}

    force = 'force' in argsdict and argsdict['force']
    sort_columns = argsdict['sort_columns'] if 'sort_columns' in argsdict else 'alphabetic'

    total_fails_by_test = {}
    total_passes_by_test = {}
    day_results = {}
    latest_year = None
    latest_yday = None
    day_fails = 0
    day_passes = 0

    for build in mongo.builds.find(builds_query).sort([('tag_time', DESCENDING)]):
        build_id = build['_id']
        build_time = (build['tag_time'] if 'tag_time' in build
                      else (['timestamp'] if 'timestamp' in build
                            else None))
        successes_for_build = {}
        failures_for_build = {}
        results_query={'build': build_id}
        interesting = False
        for result in mongo.results.find(results_query):
            if 'infrastructure_problem' not in result or result['infrastructure_problem'] == False:
                if 'test_case' in result:
                    test_case = result['test_case']
                    if (test_case != None
                        and (test_cases == None
                             or test_cases.search(test_case))
                        and (exclude_cases == None
                             or not exclude_cases.search(test_case))
                        and (force or 'experiments.py' not in test_case)):
                        if 'failure' in result and result['failure'] != '':
                            result_details = result['failure']
                            interesting = True
                            if test_case in failures_for_build:
                                failures_for_build[test_case].append(result_details)
                            else:
                                failures_for_build[test_case] = [ result_details ]
                            if test_case in total_fails_by_test:
                                total_fails_by_test[test_case] += 1
                            else:
                                total_fails_by_test[test_case] = 1
                            day_fails += 1
                        else:
                            if 'end_time' in result:
                                interesting = True
                                if test_case in successes_for_build:
                                    successes_for_build[test_case].append(result)
                                else:
                                    successes_for_build[test_case] = [ result ]
                                if test_case in total_passes_by_test:
                                    total_passes_by_test[test_case] += 1
                                else:
                                    total_passes_by_test[test_case] = 1
                                day_passes += 1
        if interesting:
            results_for_build = (build_time, successes_for_build, failures_for_build)
            gmt = gmtime(float(build_time))
            if ((gmt.tm_year != latest_year) or (gmt.tm_yday != latest_yday)):
                latest_year = gmt.tm_year
                latest_yday = gmt.tm_yday
                date_text = strftime('%Y-%m-%d', gmt)
                day_results[date_text] = (': ' + repr(day_passes) + ' passed, ' + repr(day_fails) + ' failed')
                day_fails = 0
                day_passes = 0
            results.append(results_for_build)
            results_by_build[build_id] = results_for_build
            build_ids.append(build_id)
            countdown -= 1
            if countdown == 0:
                break
        tests.update(failures_for_build.keys())
        tests.update(successes_for_build)
        if countdown == 0:
            break

    # convert from set to list
    test_names = [ test for test in tests ]

    if sort_columns == 'ratio':
        sort_text = 'Columns are sorted by decreasing ratio of fails.'
        ratios = {}
        for test in test_names:
            passes = total_passes_by_test[test] if test in total_passes_by_test else 0
            fails = total_fails_by_test[test] if test in total_fails_by_test else 0
            ratios[test] = -1 if (passes == 0 and fails == 0) else fails / (passes + fails)
        test_names = [ name for name, count in sorted(ratios.iteritems(),
                                                      key = itemgetter(1),
                                                      reverse=True) ]
    elif sort_columns == 'frequency':
        sort_text = 'Columns are sorted by decreasing number of fails.'
        frequencies = {}
        for test in test_names:
            frequencies[test] = total_fails_by_test[test] if test in total_fails_by_test else 0
        test_names = [ name for name, count in sorted(frequencies.iteritems(),
                                                      key = itemgetter(1),
                                                      reverse=True) ]
    elif sort_columns == 'alphabetic':
        sort_text = 'Columns are sorted alphabetically by test case description.'
        test_names.sort()
    else:
        sort_text = 'Columns are not sorted, as an unknown sort type "' + repr(sort_columns) + '" was specified.'

    column_number = 1
    column_numbers = {}
    column_names = [th['Test case']]
    column_keys = []
    test_labels = {}
    
    for test_name in test_names:
        test_label = test_name.replace(' ', '_')
        column_numbers[test_name] = column_number
        column_heading = th[a(href="#"+test_label, title=test_name)
                            [repr(column_number)]]
        column_names.append(column_heading)
        column_keys.append(li[a(name=test_label)
                              [a(href="http://autotest/results?reverse=1&test_case="+test_name)
                               [test_name]]])
        test_labels[test_name] = test_label
        column_number += 1

    rows = [column_names]

    latest_year = None
    latest_yday = None
    column_count = 1 + len(column_names)
    build_number_pattern = compile('.+-([0-9]+)-.+')

    day_heading_style = {'colspan':column_count, 'class':'day_heading'}
    for build_id in build_ids:
        (build_time, successes, failures) = results_by_build[build_id]
        try:
            build_number_match = build_number_pattern.match(build_id)
            build_number_string = build_number_match.group(1) if build_number_match else build_id
            gmt = gmtime(float(build_time))
            if ((gmt.tm_year != latest_year) or (gmt.tm_yday != latest_yday)):
                latest_year = gmt.tm_year
                latest_yday = gmt.tm_yday
                raw_date_text = strftime('%Y-%m-%d', gmt)
                date_text = raw_date_text
                if float(build_time) >= one_week_ago:
                    date_text += strftime(' (%A)', gmt)
                if day_results[raw_date_text] != None:
                    date_text += day_results[raw_date_text]
                rows.append([tr[th(**day_heading_style)[date_text]]])
            cells = [th(title=(build_id + '\n' + asctime(gmt)))[
                    a(href="http://autotest/build/"+build_id)[build_number_string], br(), strftime('%H:%M:%S', gmt)
                    ]]
        except TypeError:
            gmt = None
            cells = [th[a(href="http://autotest/build/"+build_id)[build_id]]]
        for test in test_names:
            success_count = len(successes[test]) if test in successes else 0
            this_test_failures = failures[test] if test in failures else None
            fail_count = len(this_test_failures) if this_test_failures != None else 0
            some_passed = success_count > 0
            some_failed = fail_count > 0
            no_results = not (some_passed or some_failed)

            if proportionate_colour:
                colour = white if no_results else rgb_string(fail_count, success_count, 0, intensity=0.5)
            else:
                several_failed = fail_count > 1
                colour = (amber if some_passed and some_failed
                          else (white if no_results
                                else ((green if success_count > 1 else pale_green) if not some_failed
                                      else (red if several_failed
                                            else pale_red))))


            cell_hover_text = test + ': ' + repr(success_count) + (' pass' if success_count == 1 else ' passes')
            if some_failed:
                # collect up identical error messages so we can just give a count instead of repeating them
                fail_detail_counts = {}
                for x in this_test_failures:
                    fail_detail_counts[x] = fail_detail_counts[x] + 1 if x in fail_detail_counts else 1

                details = [ repr(count) + ": " +
                            # display commonest error messages first
                            message for message, count in sorted(fail_detail_counts.iteritems(),
                                                                 key = itemgetter(1),
                                                                 reverse=True) if message != None]

                cell_hover_text = cell_hover_text + '\nFailures:\n' + ('\n'.join(details))
            cell_text = [div(align='left')[repr(success_count)], div(align='right')[repr(fail_count)]]
            if some_passed or some_failed:
                cells.append(td(bgcolor=colour)
                             [a(href="results?build="+build_id+"&test_case="+test,
                                title=cell_hover_text)[cell_text]])
            else:
                cells.append(td[' '])
        rows.append([tr[cells]])

    passes_row = [th['Passes']]
    fails_row = [th['Fails']]

    for test_name in test_names:
        pass_count = total_passes_by_test[test_name] if test_name in total_passes_by_test else 0
        fail_count = total_fails_by_test[test_name] if test_name in total_fails_by_test else 0
        total = pass_count + fail_count
        colour_string = 'white' if total == 0 else rgb_string(fail_count, pass_count, 0, intensity=0.5)
        passes_row.append(td(bgcolor=colour_string)[repr(pass_count)])
        fails_row.append(td(bgcolor=colour_string)[repr(fail_count)])

    rows.insert(1, tr[fails_row])
    rows.insert(1, tr[passes_row])

    column_key = [ol[column_keys]]
    table_grid = [table(border='true', style="border-collapse: collapse", align="center", width="96%")[rows]]

    title_text = 'BVT results grid for '+branch

    if ('test_cases' in argsdict
        and argsdict['test_cases'] != None
        and argsdict['test_cases'] != ''):
        title_text += ' matching "' + argsdict['test_cases'] + '"'
    if ('exclude_cases' in argsdict
        and argsdict['exclude_cases'] != None
        and argsdict['exclude_cases'] != ''):
        title_text += ' excluding "' + argsdict['exclude_cases'] + '"'

    if request != None:
        requery_form = [ table(align="center",
                               width="96%",
                               bgcolor="#f0f0f0")[
                tr()[td()['Branch: ', stan_input(name='branch',
                                                 value=branch)['']],
                     td()['Test cases: ', stan_input(name='test_cases',
                                                     value=(argsdict['test_cases']
                                                            if 'test_cases' in argsdict
                                                            else ''))[''],
                          " ",
                          'Excluded cases: ', stan_input(name='exclude_cases',
                                                         value=(argsdict['exclude_cases']
                                                                if 'exclude_cases' in argsdict
                                                                else ''))[''],
                          " ",
                          'Case-significant search', stan_input(type='checkbox',
                                     name='case')['']],
                     td()['Include malformed results:', stan_input(type='checkbox',
                                                                   name='force')['']]],
                tr()[td()['Columns sort order: ',
                          stan_input(type='radio',
                                     name='sort_columns',
                                     value='alphabetic',
                                     ** ({'checked':1} if sort_columns == 'alphabetic' else {}))['alphabetic'],
                          " ",
                          stan_input(type='radio',
                                     name='sort_columns',
                                     value='frequency',
                                     ** ({'checked':1} if sort_columns == 'frequency' else {}))['frequency'],
                          " ",
                          stan_input(type='radio',
                                     name='sort_columns',
                                     value='ratio',
                                     ** ({'checked':1} if sort_columns == 'ratio' else {}))['ratio']],
                     td()['Max results:', stan_input(name='max_results',
                                                     value=max_results)['']],
                     td()[stan_input(type='submit')]]]]
    else:
        requery_form = None

    page_contents = [title[title_text],
                     h1[title_text]]
    page_contents += [p[key_text],
                      p[sort_text],
                      table_grid,
                      h2['column key'],
                      p[sort_text],
                      column_key]

    if not proportionate_colour:
        page_contents += [h2['cell key'],
                          key_table]

    page_contents += [hr(),
                      div(align = 'right')['produced at ', asctime()]]

    return str(nevow.flat.flatten(page_contents)), str(nevow.flat.flatten(requery_form))

def cmdline_main():
    """Command line entry point."""
    parser = argparse.ArgumentParser(description="Display BVT grid")
    parser.add_argument('-o', '--output-file',
                        default = None,
                        help = 'Set the output file')
    parser.add_argument('-t', '--test-cases',
                        help = 'Include only matching test cases')
    parser.add_argument('-x', '--exclude-cases',
                        help = 'Exclude matching test cases')
    parser.add_argument('-c', '--case', action='store_true',
                        help = 'make -t and -x case-sensitive')
    parser.add_argument('-m', '--max-results',
                        type = int, default = 128 * 256,
                        help = 'Maximum results to output')
    parser.add_argument('-b', '--branch',
                        default = 'master',
                        help = 'Branch to produce grid for')
    parser.add_argument('-f', '--force',
                        help = 'Include odd-looking results')
    parser.add_argument('-s', '--sort-columns',
                        help = 'How to sort columns: alphabetic, frequency or ratio')

    args = parser.parse_args()
    outfile = open(args.output_file, 'wb')
    page_text, requery_form = testXbuild_grid(vars(args))
    outfile.write(page_text)
    outfile.close()

def make_grid_head(argsdict, request=None):
    branch = argsdict['branch'] if 'branch' in argsdict else 'master'
    page_head = [title()['BVT grid for ' + branch]]
    return str(nevow.flat.flatten(page_head))

def grid(request, constraint):
    """Web server entry point."""
    if request.method == 'GET':
        page_text, requery_form = testXbuild_grid(request.GET, request)
        return render_to_response('bvtgrid.html',
                                  RequestContext(request,
                                                 {'head': make_grid_head(request.GET, request),
                                                  'queryform': requery_form,
                                                  'content': page_text}))
    else:
        return render_to_response('generic.html',
                                  RequestContext(request,
                                                 {'content': str(nevow.flat.flatten(
                            [title['Invalid request'],
                             h1['Invalid request'],
                             p['This page supports only GET requests.']]))}))

if __name__ == '__main__':
    cmdline_main()

