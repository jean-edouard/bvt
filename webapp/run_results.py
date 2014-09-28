#
# run_results.py should give a more detailed breakdown of a test run
# especially if the test run was a suite or multiple suites.  Ideally 
# we show which steps passed and which failed per suite.
#
#



from django.shortcuts import render_to_response
from django.template import RequestContext
from pymongo import ASCENDING, DESCENDING
from src.bvtlib import mongodb
from serverlib import show_table, constraints
from serverlib.tags import a, div, tr, html_fragment
from bson import objectid
import time

CONNECTION = mongodb.get_autotest()

def status_styling(params, content, i=''):
    """Need something here for colourised content"""
    if not params.get('finish_time'):
        col = 'progress'
    elif params.get('result') == 'PASS':
        col = 'pass'
    elif params.get('result') == 'FAIL':
        col = 'failure'
    else:
        col = 'plain'
    if params.get('step%s'%i) == 'PASS':
        col = 'pass'
    if params.get('step%s'%i) == 'FAIL':
        col = 'failure'
    attrs = {'class':col}
    return tr(**attrs)[content]

def view_run_results_table(request, constraint):
    """render a table for more detailed test results, linked from results"""
    query = constraints.parse(constraint)
    oquery = dict(query)
    reverse = query.pop('reverse', 1)
    offset = query.pop('offset', 0)
    limit = query.pop('limit', 30)
    bquery = dict(query)
    status = query.pop('status', None)
    query['result_id'] = objectid.ObjectId(query['result_id'])
    print query
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

    cursor = CONNECTION.suiteresults.find(query, limit=limit, skip=offset)
    lookup = lambda term: constraints.lookup('/run_results', oquery, term)
    #x is the document in the db, .get() its attributes.
    result_columns = [
        ('Name', lambda x: (x.get('suite'))),
        ('Result', lambda x: (x.get('result'))),
        ('Command', lambda x: ('')),
        ('Time Starated', lambda x: 
            time.asctime(time.localtime(x.get('start_time')))),
        ('Time Completed', lambda x: 
            time.asctime(time.localtime(x.get('finish_time')))),
        ('Reason', lambda x:(x.get('reason')))]
    table = show_table.suite_table(
            cursor, result_columns,
            constraints.cross_reference('/results', oquery),
            offset, limit, row_fn = status_styling)
    nodes = [table]
    return render_to_response('generic.html',
                RequestContext(request, {'content':html_fragment(nodes)}))
            



