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

"""Show scheduler queue and manipulate it"""
from serverlib.tags import html_fragment, h2, form, stan_input, span
from serverlib.tags import select, option, a, div, em
from bvtlib import mongodb
from serverlib import show_table
from django.shortcuts import render_to_response
from django.template import RequestContext
from serverlib.constraints import cross_reference
from time import time, asctime, gmtime
from django.core.context_processors import csrf
from re import match
from pymongo.objectid import ObjectId
from pymongo import ASCENDING, DESCENDING
CONNECTION = mongodb.get_autotest()

def scheduler(request):
    """Render HTML"""
    def myform(text, *members):
        """Return an HTML POST form back to this page with CSRF support"""
        tok = csrf(request)
        return form(method='post', action='/scheduler')[
            stan_input(type='hidden', name='operation', value=text),
            stan_input(type='hidden', name='csrftoken', value=tok),
            list(members), stan_input(type='submit', value=text)]
    post_message = None
    if request.method == 'POST':
        operation = request.POST['operation']
        if operation == 'cancel':
            row = request.POST['id']
            query = {'_id':ObjectId(row)}
            CONNECTION.jobs.update(query, {
                    '$set': {'status': 'cancelled via web application',
                             'finish_time' : time()}})
            post_message = ['Cancelled ', row]
        elif operation == 'add to queue':
            dut = request.POST.get('dut')
            command = request.POST['command']
            if not match('((testsuite)|(experiments))[ 0-9a-zA-Z\-]+', command):
                post_message = 'invalid command '+command
            else:
                doc = {'user': request.POST['user'], 'status':'queued',
                       'submit_time': time(),
                       'timeout': int(request.POST['timeout']),
                       'urgent' : 1 if request.POST.get('urgent') else 0,
                       'dut' : dut if dut else None,
                       'command': request.POST['command'].split()}
                CONNECTION.jobs.save(doc)
                post_message = ['Added job to queue']
        else:
            assert 0
    if post_message:
        post_html = div(**{'class':'postmessage'})[
          post_message, ' ', a(href='/scheduler')[em['(clear)']]]
    else:
        post_html = []
    queue_html = []
    for title, filters, sort in [ 
        ('Queued tests', {'status':'queued'}, 
         [ ('urgent', DESCENDING),  ('submit_time', DESCENDING)]),
        ('Running tests', {'status':'running'}, 
         [('launch_time', ASCENDING)]),
        ('Recent finished tests', {'status': {'$nin':  ['queued, running']}},
         [('finish_time', DESCENDING)])]:
        cur = CONNECTION.jobs.find(filters).sort(sort)
        if 'finished' in title:
            cur = cur.limit(10)
        data= list(cur)
        columns = [
        ('user', lambda x: x.get('user')),
        ('command', lambda x: ' ' .join(x.get('command', ['no command']))),
        ('status', lambda x: a(title=x.get('failure', ''))[
                x.get('status', '(no status!)')]),
        ('dut', lambda x: x.get('dut', 'ANY')),
        ('timeout', lambda x: str(x.get('timeout'))+' seconds'),
        ('priority', lambda x: 'urgent' if x.get('urgent') else 'normal'),
        ('submission time (UT)', lambda x:
             (asctime(gmtime(x['submit_time'])) if 
              'submit_time' in x else []))]

        if title != 'Recent finished tests':
            columns.append(
                ('cancel', lambda x: myform(
                        'cancel', 
                        stan_input(type='hidden', name='id', 
                                   value=str(x['_id'])))))
        if title != 'Queued tests':
            columns.append( ('log', lambda x: 
                             a(href='/logs/job_id='+str(x['_id'])
                               )['view']))
            columns.append( ('finish time (UT)', lambda x:
                                 (asctime(gmtime(x['finish_time'])) if 
                                  'finish_time' in x else [])))
        queue = show_table.produce_table(
            data, columns, cross_reference('/scheduler', {}), show_nav=False)
        queue_html += [h2[title], (queue if data else div['(none)'])]

    dut_options = [option(value=dut['_id'])[dut['_id']] for dut 
                   in CONNECTION.duts.find()]
    
    submit_form = myform(
        'add to queue',
        span['User email address: ', 
             stan_input(type='text', name='user', size=30,
                        value='arthur.dent@example.com')],
        span[' Command: ', 
             stan_input(type='text', name='command', size=70,
                        value='experiments -n')],
        span[' DUT: ',select(name='dut')[
                option(selected='selected')['ANY'], dut_options]],
        span[' Timeout: ',
             stan_input(type='text', name='timeout', size=5, value='600')],
        span[' Urgent: ', stan_input(type='checkbox', name='urgent',value=1), ' '])

    html = [post_html, h2['Submit test job'], submit_form, queue_html]
    return render_to_response('generic.html', 
                              RequestContext(request, {
                'content': html_fragment(html)}))

