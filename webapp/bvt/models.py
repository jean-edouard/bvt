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

from urllib2 import urlopen, HTTPError
from urllib import quote
from json import loads
from re import compile

from src.bvtlib.settings import GIT_REPOSITORY_URL_FORMAT, GIT_COMMIT_URL_FORMAT
from src.bvtlib.settings import XENCLIENT_JSON_BUILDER

from src.bvtlib.mongodb import get_autotest
db = get_autotest()


def get_buildbot_data(build_id):
    try: return loads(urlopen(XENCLIENT_JSON_BUILDER + str(build_id)).read())
    except HTTPError, _:
        return None


def get_autotest_data(build_id):
    return db.builds.find_one({'buildbot_number': int(build_id)})


def get_test_results(build_tag):
    return db.results.find({"build": build_tag})


WHO_PATTERN = compile('(?P<name>[^<]+) <(?P<email>[^>]+)>')

def get_build_data(build_id):
    buildbot = get_buildbot_data(build_id)
    autotest = get_autotest_data(build_id)
    if not buildbot or not autotest:
        return None
    
    data = {
        'tag': autotest['_id'],
        'changes':[],
        'build': {
            'url': autotest['buildbot_url']
        },
        'test': {
            'duts': [],
            'results': []
        }
    }
    
    # Changes
    for change in buildbot['sourceStamp']['changes']:
        c_data = {}
        
        m = WHO_PATTERN.search(change['who'])
        c_data['name'] = m.group('name')
        c_data['email'] = m.group('email')
        
        c_data['comments'] = change['comments']
        c_data['url'] = GIT_COMMIT_URL_FORMAT % (change['repository'], change['revision'])
        
        c_data['rep'] = change['repository'].split('.')[0]
        c_data['rep_url'] = GIT_REPOSITORY_URL_FORMAT % change['repository']
        
        c_data['files'] = []
        for file in change['files']:
            f_data = {}
            f_data['path'] = file['name']
            f_data['url'] = None % (c_data['rep'], f_data['path'])
            c_data['files'].append(f_data)
        
        data['changes'].append(c_data)
    
    # Build
    if buildbot['results'] is None:
        data['build']['result_text'] = "Build In Progress"
        data['build']['class'] = 'progress'
    else:
        data['build']['result_text'] = ' '.join(buildbot['text'])
        if buildbot['results'] == 0:
            data['build']['class'] = 'pass'
        else:
            data['build']['class'] = 'failure'
    
    # Test
    results = {}
    duts = data['test']['duts']
    test_results = get_test_results(data['tag'])
    if test_results.count() == 0:
        data['test'] = None
    else:
        for r in test_results:
            if r['test_case'] not in results:
                results[r['test_case']] = {}
            
            if r['dut'] not in duts:
                duts.append(r['dut'])
            
            if r['dut'] not in results[r['test_case']]:
                results[r['test_case']][r['dut']] = {'pass':0,'tot':0,'running':0}
            s = results[r['test_case']][r['dut']]
            if 'failure' not in r:
                if 'end_time' in r:
                    s['pass'] += 1
                    s['tot'] += 1
                else:
                    s['running'] += 1
            else:
                s['tot'] += 1
        
        for test_case, r_data in results.iteritems():
            test_data = []
            for dut in duts:
                v = r_data.get(dut, {'pass':0,'tot':0,'running':0})
                
                dut_data = {}
                dut_data['summary'] = '%(pass)d/%(tot)d (%(running)d)' % v
                dut_data['url'] = '/results/build=%s/dut=%s/test_case=%s' % (data['tag'], dut, quote(test_case))
                if v['tot'] == 0:
                    if v['running'] > 0:
                        dut_data['class'] = 'progress'
                else:
                    if (float(v['pass']) / float(v['tot'])) >= 0.5:
                        dut_data['class'] = 'pass'
                    else:
                        dut_data['class'] = 'failure'
                test_data.append(dut_data)
            
            data['test']['results'].append((test_case, test_data))
    
    return data


if __name__ == '__main__':
    print get_build_data(1740)
    
