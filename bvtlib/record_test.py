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

"""Handle creation and update of result records in database"""
import sys
from pwd import getpwuid
from os import getuid, getpid
from bvtlib.mongodb import get_autotest, get_track, get_logging
from socket import gethostname
from time import time, asctime, localtime, gmtime
from bvtlib.process_result import process_result
from process_result import categorise
from bvtlib.set_build_information import set_build_information
from bvtlib.describe_dut import describe_dut
from multiprocessing import Process, Queue
from traceback import format_exception
from bvtlib.get_build import get_build
from bvtlib.settings import SMTP_ADDRESS, BVT_LAMPS, RESULTS_EMAIL_SENDER
from bvtlib.settings import RESULTS_EMAIL_RECEIVERS, DEFAULT_LOGGING
from smtplib import SMTP
from bvtlib.run import run, SubprocessError

HOSTNAME = gethostname()

def abbreviate(line):
    """Work out abbreviated commnad line"""
    spl = line.split()
    try: 
        machloc = spl.index('-m')
    except ValueError: 
        spl2 =  spl
    else: spl2 = spl[:machloc] + spl[machloc+2:]
    if 'experiments.py' in spl2[0]:
        spl3 = ['experiments.py']+spl2[1:]
    else: spl3 = spl2
    spl4 = []
    i = 1
    while i < len(spl3):
        e = spl3[i]
        if e.startswith('--'): 
            e2 = e
        elif e == '-f': 
            e2 = None
        elif  e[:1] == '-' and e[1:2] in 'agcs' and len(e)>2: 
            e2 = e[:2] +' '+e[2:]
        elif e.startswith('-'): 
            e2 = ' '.join('-'+ch for ch in e[1:])
        else: 
            e2 = e
        if e2 is not None: 
            spl4.append(e2)
        i += 1
    return spl3[0]+' ' +' '.join(spl4)

def recount(build, verbose=True):
    """Update counts in build record"""
    mdb = get_autotest()
    existing = mdb.builds.find_one({'_id':build})
    if existing is None: 
        existing = dict()
    specimens = existing.get('failure_specimens', dict())
    if type(specimens) == type([]):
        specimens = {}
    ignored = {}
    cases = 0
    for test in mdb.test_cases.find():
        if test.get('ignored_for_completion_count'):
            ignored[test['description']] = True
        else:
            cases += 1
    counts = {'passes':0, 'failures':0, 'in_progress':0,
              'infrastructure_problems':0}
    covered = {}
    for result in mdb.results.find({'build':build, 'development_mode':0}):
        testcase = result.get('test_case')
        infra = False
        code = categorise(result)
        if code in ['in_progress', 'passes']:
            pass
        elif code == 'infrastructure_problems':
            if testcase in specimens and result['_id'] == specimens[testcase]['_id']:
                del specimens[testcase]
            infra = True
        else:
            code = 'failures'
            if testcase and (testcase not in specimens or specimens[testcase]['_id'] == result['_id']):
                specimens[testcase] = result
        if testcase not in ignored and not infra:
            covered[testcase] = True
        counts[code] += 1
    counts['run_cases'] = len(covered)
    counts['total_cases'] = cases
    set_build_information(build, {'tests': counts, 
                                  'failure_specimens':specimens})
    if verbose:
        print 'RECOUNT: count for', build, counts, len(specimens)


class RecordTest:
    """A context manager that records a test to the database.
    Can also be invoked with record=False as a noop."""
    def __init__(self, record=True, reinstall_on_failure=True,
                 description=None, build=None, dut=None,
                 stdout_filter=None, result_id=None,
                 record_finish=True):
        self.record = record
        self.description = description
        self.reinstall_on_failure = reinstall_on_failure
        self.build = build
        self.dut = dut
        self.result_id = result_id
        self.mdb = self.result_id = self.dut_id = None
        self.stdout_filter = stdout_filter
        self.record_queue = self.stream_process = None
        self.record_finish = record_finish
    def __enter__(self):
        """Start recording a test"""
        try:
            run(['logger', 'BVT', 'starting', self.full_description()], 
                host=self.dut, timeout=2)
        except SubprocessError:
            print 'INFO: unable to mark test log'
        if not self.record:
            return self
        if self.result_id is None:
            self.mdb = get_autotest()
            terms = {'test_case':self.description or 'to be determined',
                     'automation_user': getpwuid(getuid()).pw_gecos.split(',')[0],
                     'control_pid' : getpid(), 'start_time' : time(),
                     'development_mode' : 0,
                     'command_line':abbreviate(' '.join(sys.argv))}
            if self.dut:
                dutdoc = self.mdb.duts.find_one({'name':self.dut})
                self.dut_id = terms['dut'] = dutdoc['_id']
                terms['dut_name'] = dutdoc['name']
                if 'development_mode' in dutdoc:
                    terms['development_mode'] = dutdoc['development_mode']
            self.result_id = self.mdb.results.save(terms)
            if self.build is None and self.dut:
                self.build = get_build(self.dut, timeout=10)
            self.mdb.results.update({'_id':self.result_id}, 
                                    {'$set':{'build':self.build}})
            if self.dut:
                self.mdb.duts.update({'_id':terms['dut']}, {'$set': {
                            'build':self.build,
                            'control_command_line': abbreviate(' '.join(sys.argv)),
                            'result_id' : self.result_id}})
        if self.stdout_filter:
            self.record_queue = Queue()
            self.stream_process = Process(
                target=service_queue, 
                args=[self.record_queue, self.result_id, 
                      self.dut, self.dut_id])
            self.stream_process.start()
            self.stdout_filter.add_callback(self, 
                                            lambda *x: self.record_queue.put(x))

        if self.description:
            print 'HEADLINE: starting', self.full_description()
        get_track().updates.save({'result_id':self.result_id,
                                  'action':'new result record'})
        return self
    def __exit__(self, _type, value, traceback):
        """Finish a test, recording the exception as a test failure,
        or regarding a test as passed if there is no exception."""
        try:
            if not self.record_finish:
                return
            print >>sys.stderr, 'record', self.record
            dutset = {'last_finish_time':time()}
            if not self.record:
                return
            upd = {'end_time': time(), 'modification_time':time()}

            if value: # i.e. , if test failed:
                upd['failure'] = repr(value)
                upd['exception'] = value.__class__.__name__
                if not isinstance(value, KeyboardInterrupt):
                    print 'HEADLINE: exception', upd['exception'], value
                    for clause in format_exception(_type, value, traceback):
                        for line in clause.split('\n'):
                            print 'CRASH:', line
                else:
                    upd['infrastructure_problem'] = True
                    upd['whiteboard'] = '[infrastructure] test interrupted'
                if self.reinstall_on_failure:
                    dutset['test_failed'] = True
                    tnext = time() + 300
                    print 'INFO: test failed, so will reinstall machine at', \
                        asctime(localtime(tnext))

            self.mdb.results.update({'_id':self.result_id}, {'$set':upd})
            classify = process_result(self.mdb.results.find_one({'_id':self.result_id}))
            print 'HEADLINE:', classify, self.full_description()

            get_track().updates.save({'result_id':self.result_id,
                                      'action':'experiment finished'})

            if self.dut_id:
                self.mdb.duts.update({'_id':self.dut_id}, 
                                     {'$unset': {'control_pid':1, 'result_id':1,
                                                 'control_command_line':1},
                                      '$set': dutset})
            if self.build:
                recount(self.build)
            if classify == 'infrastructure_problems':
                pass
            else:
                col = 'green' if classify == 'passes' else 'red'
                for lamp in BVT_LAMPS:
                    run(['xsetroot', '-display', 
                         'messageboard-north:'+str(lamp), '-solid', col])
        finally:
            if self.record_queue:
                self.record_queue.put('finish')
                self.record_queue.close()
                self.record_queue.join_thread()
            if self.stream_process:
                self.stream_process.join()
            if self.stdout_filter:
                self.stdout_filter.del_callback(self)
            
    def full_description(self):
        """Work out a full test description"""
        des = describe_dut(self.dut) if self.dut else ''
        if self.build:
            des += ' with ' + self.build
        if self.result_id:
            des += ' BVT result ID ' + str(self.result_id)
        return (self.description if self.description 
                else 'unknown test') + ' on ' +  des
    def set_description(self, description):
        """Set description (sometimes this is not known at the start
        of the test"""
        self.description = description
        if not self.record:
            return
        self.mdb.results.update({'_id':self.result_id}, 
                                 {'$set':{'test_case':description}})
    def set_build(self, build):
        """Set build (sometimes this is not known at the start of the test"""
        self.build = build
        if not self.record:
            return
        self.mdb.results.update({'_id':self.result_id}, 
                                {'$set':{'build':build}})
            
def service_queue(queue, result_id, dut, dut_id):
    """Runs in a subprocess to push stdout updates to database"""
    mdb = get_autotest()
    ldb = get_logging()
    count = 0
    while 1:
        mesg =queue.get()
        if mesg  == 'finish':
            print >>sys.stderr, '[logged %d lines to %s for %s]' % (
                count, result_id, dut)
            break
        (ts, kind, message) = mesg
        count += 1
        if type(message) ==type(''):
            message = unicode(message, encoding='utf8')
        if type(kind) == type(''):
           kind = unicode(kind, encoding = 'utf8')
        handle = '%s_%d_%f_%s' % (dut if dut else dut_id, count, ts, HOSTNAME)
    
        terms = {'message':message, 'kind': kind, 'time': ts, '_id': handle}
        if dut_id:
            terms['dut_id'] = dut_id
        if dut:
            terms['dut_name'] = dut
        if result_id:
            terms['result_id'] = result_id
        if kind in ['HEADLINE', 'RESULT'] and result_id and dut:
            rdoc = mdb.results.find_one({'_id':result_id})
            if rdoc:
                build = rdoc.get('build')
                if build:
                    set_build_information(build, 
                                          {'test_status': [ts, dut, message]})
                else:
                    print 'no build for headline'
            else:
                print 'no result for headline'
        ldb.logs.save(terms)
