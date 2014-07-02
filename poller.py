#! /scratch/autotest_python/bin/python
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

"""Poll builds and other thigns we need to know to update the database"""
import re, os, time, pprint
from bvtlib.run import run
from bvtlib import mongodb
from json import loads
from bvtlib import test_names
from bvtlib.settings import PXE_DIR, BUILD_SERVER, RELEASES_DIRECTORY
from bvtlib.settings import BUILD_REGEXP, BUILDBOT2_BUILDER_URL
from bvtlib.settings import XENCLIENT_JSON_BUILDER, XENCLIENT_BUILDER_FORMAT
from bvtlib.settings import RELEASE_REGEXP
from bvtlib.settings import MONITORED_LOCATION, MONITORED_REPOSITORY
from bvtlib.settings import BUILDBOT2_BUILDER_FORMAT, BUILDBOT2_ALL_BUILDERS_URL
from os.path import join
from update_dut_records import update_dut_records
from urllib import urlopen
from bvtlib.set_build_information import set_build_information
from bvtlib.record_test import recount
from os import listdir

MDB = mongodb.get_autotest()

def inspect_git_tags():
    """Make sure all build tags are in mongo"""
    if MONITORED_REPOSITORY is None:
        return
    assert MONITORED_REPOSITORY.endswith('.git')
    local_repo = (MONITORED_LOCATION + '/'  + 
                  MONITORED_REPOSITORY.split('/')[-1][:-4])
    if not os.path.isdir(MONITORED_LOCATION):
        run(['mkdir', '-p', MONITORED_LOCATION], verbose=False,
            cwd='/')
    repo_cmd = lambda l: run(['git']+l, cwd=local_repo, split=True,
                             verbose=True, timeout=600)
    if not os.path.isdir(local_repo):
        run(['git', 'clone', MONITORED_REPOSITORY],
            cwd=MONITORED_LOCATION, verbose=False)
    else:
        repo_cmd(['pull'])
    
    for tagl in repo_cmd(['tag']):
        if tagl == []: 
            continue
        tag = tagl[0]
        build_doc = MDB.builds.find_one({'_id':tag})
        if build_doc is None or build_doc.get('tag_time') is None:
            ref = repo_cmd(['show-ref', tag])[0][0]
            lines = repo_cmd(['cat-file', 'tag', ref])
            spl = lines[3]
            tag_time = eval(spl[-2]) + int(spl[-1][:02])*3600
            dashspl = tag.split('-')
            if len(dashspl) > 3:
                branch = '-'.join(dashspl[3:])
            else:
                branch = 'master'
            qterms = {'branch':branch, '_id':tag}
            if MDB.builds.find(qterms):
                MDB.builds.insert(qterms)
            MDB.builds.update(qterms, {'$set': {'tag_time':tag_time}})

def get_build_doc(build, branch):
    """get a mongo build document for build on branch"""
    branch = '-'.join(build.split('-')[3:])
    doc = {'_id':build, 'branch':branch}
    build_doc = MDB.builds.find_one(doc)
    if build_doc is None:
        MDB.builds.save(dict(doc, timestamp=time.time()))
        build_doc = MDB.builds.find_one(doc) # to get ID
    assert build_doc, doc
    return build_doc

def inspect_builds():
    """Make sure currents builds are in mongo"""
    if BUILD_SERVER is None:
        return
    branches_raw = run(['ls', join(PXE_DIR, 'builds')], host=BUILD_SERVER,
                       verbose=False).split()
    branches = [b for b in branches_raw if not b.startswith('cam-oeprod') and
                not b.startswith('11')]
    for branch in branches:
        target = join(PXE_DIR, 'builds', branch)
        if not os.path.isdir(target):
            continue
        for build in sorted(os.listdir(target)):
            mobj = re.match('([a-z]+)-([a-z][a-z\-]*)-([0-9]+)-(.*)', build)
            if mobj is None: 
                print 'skipping invalid tag', build, 'in', target
                continue
            site, build_type, build_id, dbranch = mobj.groups()
            if branch != dbranch:
                print 'WARNING: unexpected branch', dbranch, 'in', build, 'in', target
            build_doc = get_build_doc(build, dbranch)
            build_doc['build_type'] = build_type
            build_doc['site'] = site
            build_doc['build_id'] = int(build_id)
            mtime_epoch = int(run(["stat", "-c", "%Y", join(PXE_DIR, 'builds', branch, build)],
                                  verbose=False, split=True)[0][0])

            if build_doc.get('build_time') is None:
                print build, 'built at', \
                    time.asctime(time.localtime(mtime_epoch))
                print 'HEADLINE: new build %r branch %r' % (build, branch)
            set_build_information(build, {'build_time':mtime_epoch,
                                          'branch':dbranch,
                                          'build_type': build_type,
                                          'site':site,
                                          'build_id': build_id})

            # HACK until all test cases call recount
            recount(build, verbose=False) 

def construct_build_record(doc, build_url_pattern, builder):
    subdoc = {}
    subdoc['buildbot_number'] =doc['number'] 
    subdoc['buildbot_url']= build_url_pattern  % (builder, doc['number'])
    if doc['eta']:
        subdoc['eta_time'] =  time.time() + doc['eta']
    if len(doc.get('times', [])) == 2 and doc['times'][1]:
        subdoc['build_time'] = doc['times'][1]
    if doc.get('text') == ['exception', 'interrupted']:
        subdoc['failure'] = 'interrupted'
    if type(doc.get('steps')) == type([]):
        prev = None
        seenedge = False
        for step in doc['steps']:
            if step['text'][-1:] == ['failed'] and \
                    subdoc.get('failed') is None:
                subdoc['failure'] = ' '.join(step['text'])
                subdoc['failure_log_url'] = subdoc['buildbot_url']+ '/steps/' + step['name'] + '/logs/stdio'
            if not seenedge:
                if prev is None:
                    prevdone = True
                else:
                    prevdone = prev.get('isFinished') and \
                        prev['results'][0] == 0
                if step.get('isStarted') and prevdone:
                    if step['isFinished'] == False:
                        logurl = subdoc['buildbot_url']+'/steps/'+step['name']+'/logs/stdio/text'
                        text = ''
                        if 0:
                            print 'downloading', logurl
                            log = urlopen(logurl).read()
                            print 'read', len(log), 'from', logurl
                            for line in log.splitlines():
                                if line.startswith('NOTE:'):
                                    text = line[5:]
                                if line and text == '':
                                    text = line
                        stats = step['statistics']
                        if 'bb_current_task' in stats and \
                                'bb_task_number' in stats:
                            ex = ' step %d of %d' % (
                                stats['bb_current_task'], 
                                stats['bb_task_number'])
                        else:
                            ex = ''
                        subdoc['status'] = 'build step '+ \
                            step['name']+' running '+text+ex
                        seenedge = True
                    elif 'results' in step and step['results'][0] == 2:
                        subdoc['failure'] = ' '.join(step['text'])
                        subdoc['status'] = 'build step '+ \
                           step['name']+ ' failed'
                        seenedge = True
            prev = step
    return subdoc

def inspect_buildbot_entry(label, builder, offset, prefix):
    """Check for a specifc buildbot entry"""
    if XENCLIENT_JSON_BUILDER is None:
        return
    url =XENCLIENT_JSON_BUILDER %(builder, offset)
    text = urlopen(url).read()

    doc = loads(text)
    if 'properties' not in doc:
        return 'no properties'
    propdict = dict( [ (x[0], x[1]) for x in doc['properties']])
    for field in ['xcbuildid', 'branch']:
        if propdict.get(field) is None:
            return 'no '+field
    build = prefix + '-oeprod-' + propdict['xcbuildid'] + '-' + \
        propdict['branch']
    build_doc = get_build_doc(build, propdict['branch'])        
    updates = {}
    subdoc = construct_build_record(doc, XENCLIENT_BUILDER_FORMAT, builder)
    updates[label] = subdoc
    set_build_information(build_doc['_id'], updates)

def inspect_buildbot():
    """Read JSON data from buildbot"""
    for label, builder, prefix in [('platform', 'xenclient-release-glenn-sp1', 'cam'),
                                   ('platform', 'xenclient-release-glenn', 'cam'),
                                   ('platform', 'xenclient-master', 'cam'), 
                                   ('platform', 'xenclient-master-daily', 'daily'), 
                                   ]:
        for offset in range(-1, -10, -1):
            try:
                bad = inspect_buildbot_entry(label, builder, offset, prefix)
            except Exception, exc:
                print 'WARNING:', exc, 'examining', label, builder, offset
            else:
                if bad:
                    print 'WARNING:', bad, 'examining', label, builder, offset



def inspect_buildbot2():
    """Read buildbot2 status"""
    if BUILDBOT2_ALL_BUILDERS_URL is None:
        return
    tdoc = loads(urlopen(BUILDBOT2_ALL_BUILDERS_URL).read())
    for builder in tdoc:
        doc = tdoc[builder]
        latest = max(doc['cachedBuilds']+doc['currentBuilds'])
        for offset in range(10):
            bnum = latest - offset
            if bnum < 0:
                break
            try:
                doc = loads(urlopen((BUILDBOT2_BUILDER_URL % (builder))+'/builds/'+str(bnum)).read())
            except ValueError:
                print 'WARNING: unable to decode', builder, bnum
                continue
            #pprint.pprint(doc)
            if 'properties' not in doc:
                continue
            propdict = dict( [ (x[0], x[1]) for x in doc['properties']])
            tag = propdict.get('tag' if builder == 'XT_Tag' else 'revision')
            if tag is None:
                print 'WARNING: No tag for', builder, bnum
                continue
            if not tag.startswith('cam-oeprod-'):
                print 'WARNING: ignoring unexpected tag', tag
                continue
            build_doc = get_build_doc(tag, propdict['branch'])
            subdoc = construct_build_record(doc, BUILDBOT2_BUILDER_FORMAT, builder)
            set_build_information(tag, {builder:subdoc})
            # the deployed watcher.git expects the build record to be called platform
            # so duplicate installer builds there for now. TODO: remove this once 
            # watcher.git has been updated.
            if builder == 'XT_installer':
                set_build_information(tag,{'platform':subdoc})

def record_test_cases():
    """populate test_cases column"""
    added = set()
    count = 0
    for i, test_case in enumerate(
        test_names.make_bvt_cases()):
        added.add( test_case['description'])
        platform = False
        for _, value in test_case.get('arguments', []):
            if value == '$(DUT)':
                platform = True
        new = {'description': test_case['description'],
               'platform':platform,
               'ignored_for_completion_count': 
               test_case.get('ignored_for_completion_count', 0)}
        MDB.test_cases.update({'_id':i}, {'$set': new }, True)
        count += 1
    for row in MDB.test_cases.find():
        if row['description'] not in added:
            print 'deleting', row
            MDB.test_cases.remove({'_id':row['_id']})


def inspect_releases():
    """Examine releases directory and update builds with release names"""
    releases = {}
    for entry in sorted(listdir(RELEASES_DIRECTORY)):
        if entry == 'latest':
            release_name = entry
        else:
            mobj= re.match(RELEASE_REGEXP, entry)
            if mobj is None:
                continue
            if mobj.group(2).lower().endswith('-release'):
                release_name = mobj.group(2)[:-len('-release')]
            else:
                release_name = mobj.group(2)
        fpath = join(RELEASES_DIRECTORY, entry)
        bcontent = join(fpath, 'NOT_FOR_DISTRIBUTION')
        build = None
        if os.path.isdir(bcontent):
            bconlist = listdir(bcontent)
            for item in bconlist:
                if re.match(BUILD_REGEXP, item):
                    build = item
        if build is None:
            print 'unable to find build in', entry
            continue
        if releases.has_key(release_name):
            print 'WARNING: multiple builds for', release_name, \
                releases[release_name], 'and', build
            # we override anyway; the releases are sorted and begin by
            # date so this should reliably take the last release
            
        releases[release_name] = build
        release_doc = MDB.releases.find_one({'_id':release_name})
        if release_doc is None or release_doc.get('build') != release_name:
            MDB.releases.save({'_id':release_name, 'build':build})
        build_doc = MDB.builds.find_one({'_id':build})
        if build_doc is None:
            print 'WARNING: unknown build', build, 'for', release_name
            continue
        build_doc.setdefault('releases',list())
        creleases = build_doc['releases']
        if release_name not in creleases:
            updates= {'releases':creleases+[release_name]}
            set_build_information(build, updates)


def monitor_builds():
    """Update mongo for test_cases build tags, build trees and results"""
    inspect_buildbot2()
    inspect_builds()
    inspect_releases()
    record_test_cases()
    inspect_buildbot()
    inspect_git_tags()
    update_dut_records()
    print 'MONITOR_BUILDS: finished'

if __name__ == '__main__': 
    monitor_builds()
