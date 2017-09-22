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

"""Show duts"""
from django.shortcuts import render_to_response
from django.template import RequestContext
from src.bvtlib.mongodb import get_autotest
from pymongo import DESCENDING, ASCENDING
from serverlib.tags import html_fragment, td, a, \
    stan_input, div, h2, ol, li, tr, form, em, pre
from serverlib.show_table import produce_table
from serverlib.constraints import cross_reference, parse
from time import localtime, strftime, mktime, time
from django.core.context_processors import csrf
from subprocess import Popen, PIPE
from os import getuid
from pwd import getpwuid
from src.bvtlib.set_pxe_build import set_pxe_build
CONNECTION = get_autotest()

INSTRUCTIONS = [
    h2['OpenXT test laptop control'],
    ol[li['To allocate yourself a laptop: type your email address ',
          'in to the owner column and hit change.'],
       li['To release a laptop for scheduled tests and BVT: ',
          'clear the owner column and hit change.'],
       li['Automated test reports only include experiments ',
          'done on laptops where the publish is ticked.'],
       li['The right hand side of the page shows how many '
          'automated tes got run recently.'],
       li['Asset ID and MAC address are available as a tooltip ',
          'on the dut name']]]

def model(max_age):
    """Work out per dut usage data"""
    data = {}
    for dut in CONNECTION.duts.find():
        if 'name' not in dut:
            dut['name'] = dut['_id']
            CONNECTION.duts.save(dut)
        dut['results'] = list(CONNECTION.results.find(
                {'dut':dut['_id'],
                'end_time':{'$gt':max_age}}).sort(
                [('start_time',DESCENDING)]))
        data[dut['name']] = dut
        dut['last_update'] = CONNECTION.dut_changes.find_one(
            {'dut':dut['name']}, sort=[('epoch', DESCENDING)])
    namelist = sorted(data.keys())
    return [data[name] for name in namelist]


def run_time(x):
    """Render run time column"""
    if x.get('control_pid') is None:
        return 'no pid'
    if x.get('last_launch_time') is None:
        return 'no start'
    ex = {}
    ex['title'] = x.get('control_command_line','')+ ' PID '+str(x['control_pid'])
    
    if x.get('result_id'):
        ex['href'] = '/logs/result_id='+str(x['result_id'])
    return a(**ex)['%ds' % (time() - x['last_launch_time'])]


def countcol(t2epoch, offset):
    """Draw one cell"""
    t2epocht = localtime(t2epoch)
    t2t = strftime('%a %I%p', t2epocht).replace(' 0', ' ')
    def render(x):
        in_slice = [r for r in x['results'] if (
                    r.get('start_time') and 
                    r['end_time'] >= t2epoch and 
                    r.get('end_time', time()) <= t2epoch + 60 * 60)] 
        
        passed = len([r for r in in_slice if r.get('failure') == ''])
        completed = len(in_slice)
        if completed == 0:
            content = [0]
        else:
            content = [passed, '/', completed]
        clss = None

        if completed == 0:
            clss = 'progress'
        elif completed == passed:
            clss = 'pass'
        elif passed == 0:
            clss = 'failure'
        elif passed < completed:
            clss = 'known'
        else:
            return td[content]
        return td(Class=clss)[a(href='/results/dut_name=%s/earliest=%s' % (x['name'], t2epoch))[content]]
    return (t2t, render)

def dut_link(x):
    kw = {'href': '/results/dut_name='+x['name']}
    if 'mac_address' in x and 'asset_id' in x:
        kw['title'] = x['mac_address']+' asset ID '+x['asset_id']
    return a(**kw)[x['name']]

def whoami():
    """Return user name"""
    return getpwuid(getuid()).pw_name

def edit_row(name, label=None ,flatten = lambda x:x):
    if label is None:
        label = name
    return (label, lambda x: stan_input(type='text', width=5, name=name, value=flatten(x.get(name,''))))
    
def spacejoin(x):
    return ' '.join(x)

def duts(request, constraint):
    """Render duts table"""
    if request.method == 'POST':
        operation = request.POST.get('operation')
        if operation == 'update':

            query = {'_id': request.POST['dut']}
            olddoc = CONNECTION.duts.find_one(query)
            update = {}
            update['development_mode'] = \
                0 if request.POST.get('publish') else 1
            update['run_bvt'] = 1 if request.POST.get('run_bvt') else 0
            for field in ['owner', 'notes', 'control_machine', 
                          'power_control', 'serial_port', 'tag_regexp']:
                if field in request.POST:
                    value = request.POST[field]
                    update[field] = value
            CONNECTION.duts.update( query, {'$set': update})
            # this fails since set_pxe_build calls src.bvtlib.run.run which
            # uses signals and so can only run from main loop
            # so instead we rely on people to clear up the PXE server
            # if not update['run_bvt']:
            #     set_pxe_build(olddoc['name'], None, 'boot')
            postmessage = 'updated '+request.POST['dut']+' with '+repr(update)+' as '+whoami()
        else:
            postmessage=  'bad form operation '+repr(operation)
        post_stuff = div(**{'class':'postmessage'})[postmessage,
                                                    a(href='/duts')[em['(clear)']]]
    else:
        post_stuff = []
    t1 = time()
    data = model(time()-26*60*60)
    t2 = time()
    oquery = parse(constraint)
    query = dict(oquery)
    hours = query.pop('hours', 3)
    columns = [('dut', dut_link), 
               ('notes', lambda x: 
                stan_input(type='text', width=20, name='notes', 
                           value=x.get('notes',''))),
               ('owner', lambda x: 
                stan_input(type='text', width=20, name='owner', 
                           value=x.get('owner',''))),
               ('BVT', lambda x: stan_input(
                type='checkbox', 
                name='run_bvt', **
                ({'checked':1} if x.get('run_bvt', 0) else {}))),
               edit_row('tag_regexp'),
               edit_row('control_machine', 'control_machine'),
               edit_row('power_control', 'power'),
               edit_row('serial_port', 'serial'),
               ('publish', lambda x: stan_input(
                type='checkbox', name='publish', **({} if 
                      x.get('development_mode', 0) else {'checked':'on'}))),
               ('change', lambda x: [
                stan_input(type='hidden', name='operation', value='update'),
                stan_input(type='hidden', name='dut', value=str(x['_id'])),
                stan_input(type='hidden', name='csrftoken', 
                           value=csrf(request)),
                stan_input(type='submit', value='change')]),
               ('platform', lambda x: x.get('platform', '')),
               ('make', lambda x: x.get('make', '')),
               ('model', lambda x: x.get('model', em['run labeller!'])),
               ('memory', lambda x: '%dMB' % int(x['memory'] / (1e6)) if 
                     'memory' in x else '')]
    tt = localtime()
    ohour = tt.tm_hour
    for i in range(hours,-1, -1):
        nhour = ohour - i
        if nhour < 0:
            nhour += 24
            daybump = True
        else:
            daybump = False
        t2 = (tt.tm_year, tt.tm_mon, tt.tm_mday, nhour,
              0, 0, tt.tm_wday, tt.tm_yday, tt.tm_isdst)
        t2epoch = mktime(t2)
        if daybump: 
            t2epoch  -= 24* 60 * 60
        columns.append( countcol(t2epoch, i))
    columns.append( ('run', run_time))
    def row_fn(doc, columns):
        style = {'class':'pass'} if (doc.get('owner', '') == '' and \
                                         doc.get('run_bvt')) else {}
        return tr(**style)[form(method='post', action='/duts')[columns]]
    html = [post_stuff, 
            produce_table(data, columns, cross_reference('/duts', oquery), show_nav=False,
                          row_fn = row_fn), INSTRUCTIONS]
    return render_to_response('generic.html',
                              RequestContext(request, {
                'content': html_fragment(html)}))
