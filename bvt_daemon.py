#!/usr/bin/python

# BVTDaemon initializes a daemon that performs the following tasks:
# -Update the status on currently running tests. If the test has completed,
# remove it from the list of running tests and remove it
# from the job collection in mongo.
# -Poll the job collection for queued jobs.
# -If there are nodes free for testing, run the queued job.
# -If not, return it to the queue.
# (Note, true concurrency is maintained by autolaunch.py. BVTDaemon has
# tolerance to handle mistakes in launching jobs.)


from subprocess import Popen, PIPE
from daemon import runner
from bson import objectid
from src.bvtlib import mongodb
from src.bvtlib.settings import BUILDBOT2_ALL_BUILDERS_URL, \
    BUILDBOT2_BUILDER_URL, BUILDBOT2_BUILDER_FORMAT
from json import loads
from urllib import urlopen
from src.bvtlib.set_build_information import set_build_information
import os
import time


class BVTDaemon():
    def __init__(self):
        self.stdin_path = '/dev/null'
        self.stdout_path = '/dev/tty'
        self.stderr_path = '/dev/tty'
        self.pidfile_path = '/tmp/bvt.pid'
        self.pidfile_timeout = 5
        self.running = []

    def check_free_nodes(self, nodes_req):
        """Soft check to see if any nodes are free.  Under heavy load,
           will defer to synchronization implemented in autolaunch."""
        mdb = mongodb.get_autotest()
        cur = mdb.duts.find({'$and': [{'acquired': 0, 'enabled': 1}]})
        if int(nodes_req) <= cur.count():
            return True
        else:
            return False

    def execute_queued_job(self, job):
        """Extract the command to run from the job and
            execute it in a subprocess."""
        mdb = mongodb.get_autotest()
        command = job['command']
        nodes_req = command[command.index('-n')+1]
        command.append('--job')
        command.append(str(job['_id']))
        if self.check_free_nodes(nodes_req):  # probably safe to run the job.
            proc = Popen(command, stdout=PIPE, stderr=PIPE, stdin=PIPE,
                         shell=False, cwd=None, env={})
            self.running.append((job, proc))
            mdb.jobs.update({'_id': objectid.ObjectId(job['_id'])},
                            {'$set': {'status': 'running'}})

    def poll_job_queue(self):
        mdb = mongodb.get_autotest()
        cur = mdb.jobs.find({'status': 'queued'})
        if cur:
            for job in cur:
                self.execute_queued_job(job)

    def log_messages(self, logs, proc):
        """Do special logging here to record any errors encountered before
           autolaunch is called."""
        for line in logs[0].split('\n'):
            ts = time.time()
            handle = '%s_con_%f_%s' % ('autotest', ts, 'bvt.net')
            terms = {'message': line, 'kind': 'INFO',
                     'time': time.time(), '_id': handle,
                     'job_id': objectid.ObjectId(proc[0]['_id'])}
            mongodb.get_logging().logs.save(terms)

    def update_substatus(self):
        """Check to see if subprocess is finished.  If so, remove it from
            self.running and mark the job as finished. If we see returncode
            3, there was a problem with acquiring a node."""
        mdb = mongodb.get_autotest()
        rmv = []
        if len(self.running) > 0:
            for proc in self.running:
                proc[1].poll()
                if proc[1].returncode is not None:
                    # Node acquisition error, requeue job
                    if proc[1].returncode == 3:
                        mdb.jobs.update(
                            {'_id': objectid.ObjectId(proc[0]['_id'])},
                            {'$set': {'status': 'queued'}})
                    else:
                        logs = proc[1].communicate()
                        self.log_messages(logs, proc)
                        if proc[1].returncode == 0:
                            mdb.jobs.update(
                                {'_id': objectid.ObjectId(proc[0]['_id'])},
                                {'$set': {'status': 'Done',
                                 'finish_time': time.time()}})
                        else:
                            mdb.jobs.update(
                                {'_id': objectid.ObjectId(proc[0]['_id'])},
                                {'$set': {'status': 'Fail',
                                 'finish_time': time.time()}})
                    rmv.append(proc)
        if len(rmv) > 0:
            for job in rmv:
                self.running.remove(job)

    def run(self):
        while True:
            self.update_substatus()
            self.poll_job_queue()
            time.sleep(10)


bvtdaemon = BVTDaemon()
bvt_runner = runner.DaemonRunner(bvtdaemon)
bvt_runner.daemon_context.working_directory = os.getcwd()
bvt_runner.do_action()
