#!/usr/bin/python

from subprocess import Popen, PIPE
from daemon import runner
from bson import objectid
from src.bvtlib import mongodb
from src.bvtlib.settings import BUILDBOT2_ALL_BUILDERS_URL, \
    BUILDBOT2_BUILDER_URL, BUILDBOT2_BUILDER_FORMAT, \
    BUILDBOT_OUT_FMT, BUILDBOT_BUILD_SERVERS, \
    BUILDBOT_SITE_NAMES, AUTO_SUITE, ENABLE_BW_TEST
from json import loads
from urllib import urlopen
from src.bvtlib.set_build_information import set_build_information
import os
import time

#
#   BuildWatcher initializes a daemon that does the following tasks:
#     -Poll all buildbots for new builds at a regular internval.
#     -Update mongodb with a new entry for each build.
#     -Upon detecting a new, successful build "B", add a job to the queue
#      that invokes autolaunch with build B.


class BuildWatcher():

    def __init__(self):
        self.stdin_path = '/dev/null'
        self.stdout_path = '/dev/tty'
        self.stderr_path = '/dev/tty'
        self.pidfile_path = '/tmp/watcher.pid'
        self.pidfile_timeout = 5

    def get_build_doc(self, build, branch, site_index):
        """get a mongo build document for build on branch"""
        MDB = mongodb.get_autotest()
        doc = {'id': build, 'branch': branch}
        build_doc = MDB.builds.find_one(doc)
        if build_doc is None:
            doc['age'] = 'new'
            doc['builderName'] = build[0]
            doc['site-name'] = BUILDBOT_SITE_NAMES[site_index]
            MDB.builds.save(dict(doc, timestamp=time.time()))
            build_doc = MDB.builds.find_one(doc)
        if 'site-name' not in build_doc:
            MDB.builds.update(doc, {'$set': {'site-name':
                                    BUILDBOT_SITE_NAMES[site_index]}})
        assert build_doc, doc
        return build_doc

    def construct_build_record(self, doc, url_pattern, builder, build_doc):
        """Parse the buildbot JSON to create an inner build record in the
           build document in mongo."""
        subdoc = {}
        subdoc['buildbot_number'] = doc['number']
        subdoc['buildbot_url'] = url_pattern % (builder, doc['number'])
        url_tmp = subdoc['buildbot_url'].split('/')[2].split(':')[0]
        subdoc['server_url'] = url_tmp
        if doc['eta']:
            subdoc['eta_time'] = time.time() + doc['eta']
        if len(doc.get('times', [])) == 2 and doc['times'][1]:
            subdoc['build_time'] = doc['times'][1]
        if doc.get('text') == ['exception', 'interrupted']:
            subdoc['failure'] = 'interrupted'
        if isinstance(doc.get('steps'), __builtins__.list):
            prev = None
            seenedge = False
            for step in doc['steps']:
                if step['text'][-1:] == ['failed'] and \
                        subdoc.get('failed') is None:
                    subdoc['failure'] = ' '.join(step['text'])
                    subdoc['failure_log_url'] = subdoc['buildbot_url'] \
                        + '/steps/' + step['name'] + '/logs/stdio'
                if not seenedge:
                    if prev is None:
                        prevdone = True
                    else:
                        prevdone = prev.get('isFinished') and \
                            prev['results'][0] == 0
                    if step.get('isStarted') and prevdone:
                        if step['isFinished'] == False:
                            logurl = subdoc['buildbot_url'] \
                                + '/steps/'+step['name'] + '/logs/stdio/text'
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
                            subdoc['status'] = 'build step ' + \
                                step['name'] + ' running ' + text + ex
                            seenedge = True
                        elif 'results' in step and step['results'][0] == 2:
                            subdoc['failure'] = ' '.join(step['text'])
                            subdoc['status'] = 'build step ' \
                                + step['name'] + ' failed'
                            seenedge = True
                prev = step
        if 'failure' in subdoc:
            build_doc['failure'] = True
        if ('status' in subdoc) and ('running' in subdoc['status']):
            build_doc['finished'] = False
        else:
            build_doc['finished'] = True
        mongodb.get_autotest().builds.update(
                    {'id': build_doc['id']}, {'$set': build_doc})
        return subdoc

    def job_queued_or_running(self, build):
        """Verify if there is a running or queued job for a particular build.
           Once we make sure there is a job, we can mark that build as 'old' so
           no new jobs are scheduled for it."""
        mdb = mongodb.get_autotest()
        cur = mdb.jobs.find({'status': 'queued'})
        cur_run = mdb.jobs.find({'status': 'running'})
        for job in cur:
            if ('new-build-tests' in job['command']) and \
              (BUILDBOT_OUT_FMT % (build['site-name'],
               build['id'][1], build['branch']) in job['command']):
                return True

        for job in cur_run:
            if ('new-build-tests' in job['command']) and \
              (BUILDBOT_OUT_FMT % (build['site-name'],
               build['id'][1], build['branch']) in job['command']):
                return True

        return False

    def set_builds_old(self):
        mdb = mongodb.get_autotest()
        cur = mdb.builds.find({'age': 'new'})
        if cur is None:
            return
        for build in cur:
            if self.job_queued_or_running(build):
                mdb.builds.update({'id': build['id']},
                                  {'$set': {'age': 'old'}})

    def inspect_buildbot(self):
        """Inspect all of the buildbot instances listed in the settings file.
           Ignore any tools builders."""
        for server in BUILDBOT_BUILD_SERVERS:
            try:
                tdoc = loads(urlopen(server).read())
            except Exception:
                print 'ERR: Server unreachable, trying next server.'
                continue
            for builder in tdoc:
                if 'win' in builder or 'cent' in builder:
                    continue
                doc = tdoc[builder]
                if doc['cachedBuilds'] == [] and doc['currentBuilds'] == []:
                    continue
                latest = max(doc['cachedBuilds'] + doc['currentBuilds'])
                for offset in range(10):
                    bnum = latest - offset
                    if bnum < 0:
                        break
                    try:
                        target = server + '/%s' % (builder) + '/builds/'
                        doc = loads(urlopen(target + str(bnum)).read())
                    except ValueError:
                        print 'WARNING: unable to decode', builder, bnum
                        continue
                    if 'properties' not in doc:
                        print 'Props not in doc'
                        continue
                    propdict = dict([(x[0], x[1]) for x in doc['properties']])
                    tag = propdict.get(
                            'tag' if builder == 'XT_Tag' else 'revision')
                    name = [doc['builderName'], str(bnum)]
                    s = BUILDBOT_BUILD_SERVERS.index(server)
                    build_doc = self.get_build_doc(name, propdict['branch'], s)
                    subdoc = self.construct_build_record(
                            doc, server+'/%s/builds/%d', builder, build_doc)
                    set_build_information(name, {builder: subdoc})

    def make_job(self, build):
        """Queue a job that will run new-build-tests on a
             freshly completed build."""
        job = {}
        job['status'] = 'queued'
        job['urgent'] = 0
        job['command'] = \
            ['./autolaunch.py',
             '-n', '1', '--suite', "%s" % AUTO_SUITE,
             '--server', "%s" % build[build['builderName']]['server_url'],
             '--build', BUILDBOT_OUT_FMT % (build['site-name'], build['id'][1],
                                            build['branch'])]
        job['user'] = 'bvt'
        job['timeout'] = 3600
        job['submit_time'] = time.time()
        job['dut'] = 'ANY'
        return job

    def test_new_builds(self):
        mdb = mongodb.get_autotest()
        cur = mdb.builds.find({'age': 'new', 'finished': True,
                              'failure': {'$exists': False}})
        for build in cur:
            name = build['builderName']
            job = self.make_job(build)
            mdb.jobs.save(job)

    def pretend_test(self):
        """Test function when we don't actually want to queue a job."""
        mdb = mongodb.get_autotest()
        cur = mdb.builds.find({'age': 'new', 'finished': True,
                              'failure': {'$exists': False}})
        print 'In Test_func'
        for build in cur:
            name = build['builderName']
            print 'New build to test.'
            print build

    def new_builds(self):
        mdb = mongodb.get_autotest()
        cur = mdb.builds.find({'age': 'new'})
        if cur is None:
            return False
        for build in cur:
            if mdb.builds.find({'id': build['id'],
                               'failure': {'$exists': False}}):
                return True
        return False

    def run(self):
        while True:
            self.inspect_buildbot()
            if ENABLE_BW_TEST and self.new_builds():
                self.test_new_builds()
                self.set_builds_old()
            time.sleep(60)

builddaemon = BuildWatcher()
build_runner = runner.DaemonRunner(builddaemon)
build_runner.daemon_context.working_directory = os.getcwd()
build_runner.do_action()
