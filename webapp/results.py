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

"""show the mongodb results collection as a table"""
from django.shortcuts import render_to_response
from django.template import RequestContext
from pymongo import ASCENDING, DESCENDING
from src.bvtlib import mongodb
from serverlib import show_table, constraints
from serverlib.tags import a, div, tr, html_fragment
import time

CONNECTION = mongodb.get_autotest()

def status_styling(params, content):
    """make a tr containng content colourised according to params"""
    if not params.get('end_time'): 
        col = 'progress'
    elif params.get('end_time') and not params.get('failure'): 
        col = 'pass'
    elif params.get('failure') and params.get('whiteboard'): 
        col = 'known'
    elif params.get('failure'): 
        col = 'failure'
    else:
        col = 'plain'
    attrs = {'class':col}
    return tr(**attrs)[content]


def view_results_table(request, constraint):
    """render a table of HTML results in a clean way"""
    query = constraints.parse(constraint)
    oquery = dict(query)
    reverse = query.pop('reverse', 1)
    offset = query.pop('offset', 0)
    limit = query.pop('limit', 30)
    bquery = dict(query)
    status = query.pop('status', None)
    if status == 'unknown_failures':
        query['whiteboard'] = ''
        query['failure'] = {'$exists': True, '$ne':''}
        query['end_time'] = {'$exists':True}
    elif status == 'product_problems':
        query['whiteboard'] = {'$exists': True, '$ne':''}
        query['infrastructure_problem'] = False
        query['end_time'] = {'$exists':True}
        query['failure'] = {'$exists': True, '$ne':''}
    elif status == 'infrastructure_problems':
        query['whiteboard'] = {'$ne':''}
        query['infrastructure_problem'] = True
        query['end_time'] = {'$exists':True}
    elif status == 'failures':
        query['infrastructure_problem'] = False
        query['failure'] = {'$exists': True, '$ne':''}
        query['end_time'] = {'$exists':True}
    elif status == 'passes':
        query['failure'] = ''
        query['end_time'] = {'$exists':True}
    elif status:
        return render_to_response(
            'generic.html', 
            RequestContext(request, {'content':html_fragment(
                ['invalid status '+repr(status)])}))
    earliest = query.pop('earliest', None)
    latest = query.pop('latest', None)
    if earliest:
        query['start_time'] = {'$gt':float(earliest)}
    elif latest:
        query['start_time'] = {'$lt':float(latest)}
    else:
        query['start_time'] = {'$exists': True}
    if query.get('whiteboard') == '':
        q2=dict(query)
        q2['whiteboard'] = { '$exists' :False}
        query = {'$or': [query, q2]}
    cursor = CONNECTION.results.find(query, limit=limit, 
                                     skip=offset).sort(
                'start_time', DESCENDING if reverse else ASCENDING) 

    lookup = lambda term: constraints.lookup('/results', oquery, term)
    result_columns = [ 
        ('mode', lambda x: 'DEVELOPMENT' if x.get('development_mode') 
         else 'PRODUCTION'),
        ('Test Suite/Step information', lambda x: a(href='/run_results/result_id='+str(x['_id']))[str(x['_id'])]),
        lookup('test_case'),
        ('start time',  lambda x: time.asctime(
                time.localtime(x.get('start_time')))),
        ('end time',  lambda x: 
         time.asctime(time.localtime(x.get('end_time'))) if 
         x.get('end_time') else 'still running'),
        constraints.lookup('/results', oquery, 'dut_name'), 
        lookup('build'),
        ('result', lambda x: (x.get('failure', 'PASS') if 
                              x.get('end_time') else 'unfinished')),
        ('server', lambda x: x.get('automation_server', '-')),
        ('pid', lambda x: x.get('control_pid', '-')),
        ('whiteboard', lambda x: x.get('whiteboard','') or '-')]
    if earliest is None and latest is None:
        result_columns += [('history', lambda x: a(
                    href='/results/dut='+x.get('dut_name', '-')+
                    '/reverse=1/latest='+str(x.get('end_time') or x['start_time']))['context'] if
                            x.get('dut') and x.get('start_time') else '-')]
    result_columns += [('log file', lambda x: a(href='/logs/result_id='+str(x['_id']))['view'])]

    table = show_table.produce_table(
        cursor, result_columns, 
        constraints.cross_reference('/results', oquery),
        offset, limit, row_fn = status_styling)
    nodes = [
        div['there are ', CONNECTION.results.count(),
            ' results and this page shows the most recent starting at offset ',
            offset],
        table
    ]
    return render_to_response('generic.html',
                RequestContext(request, {
                    'content': html_fragment(nodes)
                }))
