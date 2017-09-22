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

from django.shortcuts import render_to_response
from django.template import RequestContext
from serverlib.tags import html_fragment, h2, a
from src.bvtlib import mongodb, process_result
from serverlib import show_table, constraints, describe_build
from webapp import status_styling
from django.conf.urls.defaults import patterns
import pymongo

CONNECTION = mongodb.get_autotest()


def model(build, oquery):
    duts = {}
    records = []
    counters = {None:{}}
    for result in CONNECTION.results.find({'build':build}):
        if result.get('end_time') is None:
            continue
        duts[result.get('dut_name')] = True
        field = process_result.categorise(result)
        for key in [ (None, result['test_case']),
                     (result.get('dut_name'), result['test_case'])]:
            counters.setdefault(key, {})
            counters[key].setdefault(field, 0)
            counters[key][field] += 1
    
    for dut in [None]+sorted(duts):
        cases = []
        for test_case in CONNECTION.test_cases.find().sort(
            [('_id',pymongo.ASCENDING)]):
            if dut and not test_case['platform']:
                continue
            des = test_case['description']
            cases.append( dict(counters.get( (dut, des), {} ),
                               test_case=test_case,
                               build=build, dut=dut))
        records.append( (dut, cases) )
    return records


def build_report(request, build, constraint):
    query = constraints.parse(constraint)
    oquery = dict(query)

    if build == 'latest':
        build_doc = CONNECTION.builds.find_one(
            {'branch':'master', 
             'build_time':{'$exists':1}},
            sort=[('build_time', pymongo.DESCENDING)])
        if build_doc:
            build = build_doc['_id']
    else:
        build_doc = CONNECTION.builds.find_one( {'_id':build})
    branch = '-'.join(build.split('-')[3:])
    records = model(build, oquery)

    builddocs = [build_doc]
    try:
        build_prev = CONNECTION.builds.find({'branch': build_doc['branch'],
                                             'build_time' : {'$lt': build_doc['build_time']}}).sort(
            [('build_time',pymongo.DESCENDING)]).limit(1)[0]
    except (IndexError, KeyError), _:
        pass
    else:
        builddocs = [build_prev] + builddocs
                                      
    try:
        build_next = CONNECTION.builds.find({'branch': build_doc['branch'],
                                             'build_time' : {'$gt': build_doc['build_time']}}).sort(
            [('build_time',pymongo.ASCENDING)]).limit(1)[0]
    except (IndexError, KeyError), _:
        pass
    else:
        builddocs += [build_next]

    builds = [b['_id'] for b in builddocs]

    html = [describe_build.build_navigation(builds, build),
            describe_build.describe_build(branch, build)]
    columns = [('description', lambda x: a(
                href='/results/build='+x['build']+'/test_case='+
                x['test_case']['description']+
                ('/dut='+x['dut'] if x.get('dut_name') else ''))[
                x['test_case']['description']])]

    for dut, stuff in records:
        columns2 = list(columns)
        for name in process_result.CATEGORIES:
            def render(field, dut):
                def fn(x):
                    url = '/results/status='+field+'/build='+build+'/test_case='+x['test_case']['description']
                    if dut:
                        url += '/dut='+dut
                    return a(href=url)[x.get(field,0)]
                return fn

            columns2.append(  (name.replace('_', ' '), render(name, dut)) )
        dutdoc = CONNECTION.duts.find_one({'name': dut})
        des = []
        for field in ['make', 'model', 'memory']:
            if dutdoc and dutdoc.get(field): 
                v = dutdoc[field]
                if field == 'memory':
                    v = '%.03fGiB' % (v / (2.0**30))
                des += [v, ' ']
        if des:
            des += [ '(', dut, ')']
        else:
            des += [ dut ]
        tab = show_table.produce_table(
            stuff, columns2, 
            constraints.cross_reference('/build/'+build, oquery),
            offset=0, show_rows=0, row_fn=status_styling.status_styling)
        html += [h2['Results for build ',build, 
                    [' on ',des,] if dut else [' across all test machines']],tab]

    return render_to_response('generic.html',
                              RequestContext(request, {
                'content': html_fragment(html)}))

constraint = '((?:/[a-z_]+=[0-9a-zA-Z\-\.\ ]+)*)'

urlpatterns = patterns('webapp.build_report',
    (r'([a-zA-Z\-0-9]+)'+constraint, 'build_report')
)
