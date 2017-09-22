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

"""Render a log segment to HTML"""
from django.shortcuts import render_to_response
from django.template import RequestContext
from pymongo import ASCENDING
from bson import objectid
from src.bvtlib.settings import DEFAULT_LOGGING
from src.bvtlib.record_test import recount
from src.bvtlib import mongodb 
from serverlib.tags import html_fragment, div, span, a, tr, form, stan_input, em
from serverlib import show_table, constraints
import time

CONNECTION = mongodb.get_autotest()
LOGDB = mongodb.get_logging()


def row_styling(params, content):
    """Style rows according to CSS"""
    attrs = {'class': params['kind']}
    return tr(**attrs)[content]

def logs_table(request, constraint):
    """renders the latest entries in the logs capped collection"""
    query = constraints.parse(constraint)
    oquery = dict(query)
    offset = query.pop('offset', 0)
    limit = query.pop('limit', 1000)
    show = query.pop('show', DEFAULT_LOGGING)
    if query.get('result_id'):
        rid = query['result_id'] = objectid.ObjectId(query['result_id'])
        rdoc = CONNECTION.results.find_one({'_id':rid})
    else:
        rid = None
    if query.get('job_id'):
        query['job_id'] = objectid.ObjectId(query['job_id'])


    if rid and request.method == 'POST':
        wb = request.POST.get('whiteboard')
        CONNECTION.results.update({'_id':rid}, {
                '$set': 
                {'whiteboard':wb, 'infrastructure_problem': True 
                 if '[infrastructure]' in wb else False}})
        build = rdoc.get('build')
        if build:
            recount(build)
        postmessage = div(Class='postmessage')[
            'updated results for ',str(rid), ' with whiteboard ', wb, ' ',
            a(href=request.path)[em['clear']]]
    else:
        postmessage = []
    showset = [x for x in show.split(',') if x]
    kindset = LOGDB.logs.find(query).distinct('kind')
    query['kind'] = {'$in': showset}
    cursor = list(LOGDB.logs.find(query).skip(offset).limit(limit))
    query.pop('kind')
    for row in cursor:
        for key in ['result_id', 'job_id']:
            if key in row:
                row[key] = str(row[key])
    lookup = lambda term: constraints.lookup('/logs', oquery, term)
    query['show'] = show

    log_columns = [
        ('time',  lambda x: '%.3fs' % (x['time'] - cursor[0]['time'])),
        ('kind', lambda x: x['kind']),
        ('message', lambda x: div(Class='log')[x['message']])]

    if 'result_id' not in query:
        log_columns += [
            ('server', lambda x: x.get('automation_server','?')),
            lookup('dut'), lookup('dut_name'),
            lookup('result_id'), lookup('job_id'),
            lookup('pid')]

    if cursor == []:
        rel = []
    else:
        rel = div['Times are relative to ',
                  time.asctime(time.localtime(cursor[0]['time'])), 
                  ' counting from ',offset, ' of ', LOGDB.logs.count()]
    table = show_table.produce_table( 
        cursor, log_columns,  
        constraints.cross_reference('/logs', query),
        offset=offset, show_rows=limit, row_fn = row_styling)
    
    showfilter = []
    q1 = dict(query)
    if 'show' in q1:
        del q1['show']
    print 'kindset', kindset, 'showset',  showset
    for term in sorted(kindset):
        if term in showset:
            continue
        nlist = showset+[term]
        q2 = dict(q1, show=','.join(nlist))
        rel = '/logs'+constraints.unparse(q2)
        showfilter.append ( [span[a(href=rel)['show ',term]], ' '])
    if rid:
        ex = {}
        rdoc = CONNECTION.results.find_one({'_id':rid})
        if 'whiteboard' in rdoc:
            ex['value'] = rdoc['whiteboard']
        setwb = form(method='post', action='/logs/result_id='+str(rid))[
            'whiteboard=',
            stan_input(type='text', size=150, name='whiteboard', **ex),
            stan_input(type='submit', value='update')]
        download = div[a(href="/logdownload/"+str(rid))[
            'Download complete log file']]
    else:
        setwb = []
        download = []
    
    return render_to_response('generic.html',
                RequestContext(request, {
                    'content': html_fragment([postmessage, download, setwb,
                                              showfilter,rel,table])}))
