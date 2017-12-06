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

"""Update analytics for a new result"""

import re, time
from time import asctime, localtime
from pprint import pprint
from mongodb import get_autotest, get_track, get_logging, DESCENDING

CLASSIFIER_FIELDS = ['test_case', 'dut_name', 'failure', 'earliest_build', 
                     'latest_build', 'result_id', 'log_entry']

def field_name(key):
    """generate mongo field name"""
    return key+('_regexp' if key != 'earliest_build' and key != 'result_id'
                else '')

def check_classifier(mongo, classifier, result, verbose=False):
    """Does classifier match result?"""
    if verbose:
        print 'CLASSIFIER: running analyser:', classifier
    if not classifier.get('owner'):
        if verbose:
            print 'CLASSIFIER: rejecting due to lack of owner'
        return False
    result_id_need = classifier.get('result_id')
    if result_id_need not in [None, result['_id']]:
        if verbose:
            print 'CLASSIFIER: rejecting due to result ID mismatch'
        return False
    for key in CLASSIFIER_FIELDS:
        field = field_name(key)
        classifier_value = classifier.get(field)
        if classifier_value is None:
            continue
        if key == 'result_id':
            result_value = result['id']
            condition = lambda: classifier_value == result_value
        elif key in ['earliest_build', 'latest_build'] and 'build' in result:
            limit = mongo.builds.find_one({'_id':classifier_value})
            if limit is None:
                continue
            this_result = mongo.builds.find_one({'_id':result['build']})
            if this_result is None:
                if verbose:
                    print 'CLASSIFIER: rejecting due to non existent build value in result'
                return False
            result_value = this_result.get('tag_time')
            if result_value is None:
                if verbose:
                    print 'CLASSIFIER: rejecting due to missing tag_time and', key, 'specified'
                return False
            if key == 'earliest_build':
                condition = lambda: limit['tag_time'] <= this_result['tag_time']
            else:
                condition = lambda: limit['tag_time'] >= this_result['tag_time']
        elif key == 'log_entry':
            if classifier_value:
                match =get_logging().logs.find_one(
                    {'result_id':result['_id'], 'kind': {'$ne': 'CLASSIFIER'},
                     'message': {'$regex':classifier_value}})
                if match:
                    continue
                else:
                    if verbose:
                        print 'CLASSIFIER: rejecting', result['_id'], 'due to no log match', classifier_value
                    return False
            else:
                return False
            condition = lambda: match
        else:
            if result.get(key) is None:
                if verbose:
                    print 'CLASSIFIER: rejecting', classifier, \
                        'due to absence of', key, 'in result'
                return False
            rvalue = result[key]
            if key == 'dut' and result.get('dut_name'):
                rvalue = result['dut_name']
            condition = lambda: re.search(classifier_value, rvalue)
            result_value = rvalue
        if not condition():
            if verbose:
                print 'CLASSIFIER: rejecting due to', key, 'mismatch on', result_value
            return False
        else:
            if verbose:
                print 'CLASSIFIER: passed', key
    if verbose:
        print 'CLASSIFIER: accepting for', classifier
    return True

CATEGORIES = ['passes', 'product_problems', 'infrastructure_problems',
              'unknown_failures']

SUMMARY_CATEOGRIES = ['passes', 'failures']

def categorise(result):
    """Categorise a result as pass/known_problems/unknown_failures"""
    if result.get('end_time') is None:
        return 'in_progress'
    elif not result.get('failure'):
        return 'passes'
    elif result.get('infrastructure_problem'):
        return 'infrastructure_problems'
    elif result.get('whiteboard'):
        return 'product_problems'
    else: 
        return 'unknown_failures'

def process_result(result, mongo=None, verbose=True, replace=False):
    """Update analytics for a new result"""
    for key in ['end_time', 'test_case']:
        if result.get(key) is None:
            return 'incomplete'
    orig_whiteboard = result.get('whiteboard')
    if verbose:
        print 'CLASSIFIED: existing whiteboard', orig_whiteboard
    if verbose:
        print 'CLASSIFIER: examining', result,
        if result.get('end_time'):
            print asctime(localtime(result['end_time']))
        print
    whiteboard = ''
    if mongo is None:
        mongo = get_autotest()
    for classifier in mongo.classifiers.find():
        miss = not check_classifier(mongo, classifier, result, verbose=verbose)
        if miss: 
            continue
        if replace or result.get('whiteboard') is None:
            if verbose:
                print 'CLASSIFIER: selecting', classifier, 'for', result, \
                    time.asctime(time.localtime(result['end_time']))
        whiteboard = classifier['whiteboard']
    if verbose:
        print 'CLASSIFIER: set whiteboard', whiteboard
    mongo.results.update(
        {'_id': result['_id']}, 
        {'$set': {'failure': result.get('failure', ''),
                  'whiteboard': whiteboard if whiteboard else '',
                  'infrastructure_problem': True if whiteboard and 
                  '[infrastructure]' in whiteboard else False}})
    if whiteboard != orig_whiteboard:
        get_track().updates.save({'action':'new whiteboard entry',
                                  'result_id':result['_id']})
    return categorise(result)

