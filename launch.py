#! /scratch/autotest_python/bin/python
#
# Copyright (c) 2014 Citrix Systems, Inc.
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

import sys, time, os
from optparse import OptionParser
from sys import exit
from socket import gethostname
from bvtlib.pxe_install_xc import XT_INSTALL_TEST_CASE
from bvtlib.validate_dut_name import validate_dut_name
from bvtlib import test_names, mongodb
from bvtlib.get_build import get_build
from bvtlib.make_log_entry import make_log_entry
from bvtlib.domains import list_vms
from bvtlib.time_limit import TimeoutError
from bvtlib.run import run, SubprocessError
from bvtlib.wait_to_come_up import wait_to_come_up
from bvtlib.store_status_report import store_status_report
from bvtlib.settings import DEFAULT_TAG_REGEXP
from bvtlib.console_logging import ConsoleMonitor
from bvtlib.time_limit import time_limit
from bvtlib.stdout_filter import StdoutFilter
from bvtlib.record_test import RecordTest
from infrastructure.xt.decode_tag import extract_branch
from bvtlib.domains import name_split
from re import match
from traceback import print_exc
from os.path import abspath, split

def get_tag_regexp(dut):
    """Return the list of branches that dut should test"""
    mdb = mongodb.get_autotest()
    dutdoc = mdb.duts.find_one({'name':dut})
    return dutdoc.get('tag_regexp', DEFAULT_TAG_REGEXP)

class NoMatchingBuilds(Exception):
    """No builds on required branch"""

class NoMatchingTests(Exception):
    """No tests are possible in this configuration"""

def latest_build(dut):
    """Return the most recent build on branch as a tag name string"""
    mdb = mongodb.get_autotest()
    print 'LATEST: finding latest build for', dut
    tag_regexp = get_tag_regexp(dut)
    print 'LATEST: finding latest build matching', tag_regexp
    build =  mdb.builds.find_one(
        {'_id':{'$regex':tag_regexp}, 'suppress' : {'$exists':0}}, 
        sort=[('build_time', mongodb.DESCENDING)])
    if build is None:
        raise NoMatchingBuilds(tag_regexp)
    print 'LATEST: latest build matching', tag_regexp, 'is', build['_id']
    return build['_id']

def is_test_available(case, dut, current_install, domlist, build):
    """Can we run case on dut? Return boolean and a reason why not"""
    unsuitable = case.get('unsuitable_duts', list())
    if dut in unsuitable:
        return False, dut+' unsuitable'
    if current_install and case['trigger'] in ['first', 'platform install']:
        return False, 'restricted to current install'
    guest = case.get('guest')
    if guest is not None:
        guest_os_name, _ = name_split(guest)
    else:
        guest_os_name = None
    if guest and case.get('trigger') != 'VM install':
        if not [dom for dom in domlist if dom['name'] == guest
                and dom['status'] == 'running']:
            return False, "requires "+guest+" VM"
    if 'futile' not in case:
        futile = ''
    else:
        try:
            with time_limit(10, 'futility check'):
                futile = case['futile'](dut, guest, guest_os_name, build, domlist) 
        except Exception, exc:
            print_exc()
            futile = 'futility check failed %r' % exc
    if futile:
        return False, futile
    return True, ''

def choose_test(dut, current_install=False, test_case_regexp=None):
    """select a test for dut"""
    mdb = mongodb.get_autotest()
    minimum_n = minimum = None
    current_build = get_build(dut, timeout=20)
    domlist = []
    if current_build:
        try:
            domlist = list_vms(dut)
        except Exception, exc:
            print 'INFO: unable to list domains', exc
    print 'CHOOSE: current build', current_build
    if mdb.duts.find_one({'name':dut}).get('test_failed') and \
            not current_install:
        print 'CHOOSE: machine has failed test, so will test latest build'
        if test_case_regexp and not match(test_case_regexp, 
                     XT_INSTALL_TEST_CASE['description']):
            raise NoMatchingTests(dut, test_case_regexp)
        return XT_INSTALL_TEST_CASE, latest_build(dut)
    print 'CHOOSE: considering build', latest_build(dut)
    print 'BUILD_DETAILS: current build', current_build
    if current_install:
        build = current_build
        if build is None:
            print 'ERROR: -c specified but build cannot be determined'
            sys.exit(1)
    else:
        build = latest_build(dut)
        if build is None:
            print 'ERROR: build not specified for', dut
            sys.exit(2)            
    for case in test_names.make_bvt_cases():
        if (test_case_regexp and 
            not match(test_case_regexp, case['description'])):
            continue
        available, futile = is_test_available(case, dut, 
                                              current_install, domlist, build)
        num = mdb.results.find({'build':build, 
                                'test_case':case['description']}).count()
        print 'CHOOSE: results=%03d status=%12s %30s for=%s' % (
            num, ('RUNNABLE' if available else 'BLOCKED'), futile,
            case['description'])
        if minimum is None:
            preferable = True
        else:
            if (minimum_n == num and build == current_build and 
                minimum[1] != build):
                # this is equally as necessary, but will be quicker to 
                # run since the build is already installed
                preferable = True
            else:
                preferable = minimum_n > num

        if available and preferable:
            minimum = case, build
            minimum_n = num

    if minimum is None:
        print 'ERROR: no tests available'
        exit(3)
    test_case, build = minimum
    if current_build != build: 
        print 'CHOOSE: will install', build, 'instead of', current_build
        if (test_case_regexp is not None and 
            not match(test_case_regexp, XT_INSTALL_TEST_CASE['description'])):
            raise NoMatchingTests(dut, test_case_regexp)
                        
        return XT_INSTALL_TEST_CASE, build

    print 'CHOOSE: will do', test_case, 'on', build
    return (test_case, build)

def do_test(dut, test_case, build, result_id, source_directory):
    """Run test_case on dut using build"""
    if test_case['trigger'] != 'platform install':
        wait_to_come_up(dut)
    
    handles = [handle for handle, human in test_names.ordering if 
               human in test_case]
    handle = handles[0] if handles else None
    
    arg_dict = {}
    guest = test_case.get('guest')
    for name, value in test_case['arguments']:
        if value == '$(DUT)':
            valuep = dut
        elif value  == '$(GUEST)':
            valuep = test_case['guest']
        elif value == '$(OS_NAME)':
            if guest is None:
                valuep = 'dom0'
            else: 
                valuep = dict(test_names.ordering).get(guest, guest)
        elif value == '$(RELEASE)':
            valuep = None
        elif value == '$(BUILD)':
            valuep = build
        elif value == '$(PRESERVE_DATABASE)':
            valuep = False
        elif value == '$(SOURCE_DIRECTORY)':
            valuep = source_directory
        elif value == '$(SYNCH_URL)':
            valuep = 'autoxt1.cam.xci-test.com'
        elif value == '$(ENCRYPT_VHD)':
            valuep = False
        elif value == '$(RESULT_ID)':
            valuep = result_id
        elif value == '$(UPDATE_BRANCH)':
            valuep = extract_branch(build)
        elif value == '$(UPDATE_BUILD)':
            valuep = build
        else:
            valuep = value
        arg_dict[name] = valuep
    test_case['function'](**arg_dict)

def get_job(mdb, dut):
    """Find the next job for dut in mdb"""
    for settings in [{'dut':dut, 'urgent':1},
                     {'urgent':1},
                     {'dut':dut},
                     {}]:
        job = mdb.jobs.find_one(dict(settings, status='queued'))
        if job:
            return job

def one_operation(options):
    """Launch a single operation"""
    mdb = mongodb.get_autotest()
    
    dut_document = mdb.duts.find_one({'name':options.machine})

    with StdoutFilter(verbose=options.verbose) as recording:
        with RecordTest(record=True, dut=options.machine,
                         stdout_filter=recording) as recording:
            with ConsoleMonitor(options.machine, recording.result_id):
                one_operation_logged(options, recording)

def one_operation_logged(options, recording):
    try:
        mdb = mongodb.get_autotest()
        dut_document = mdb.duts.find_one({'name':options.machine})

        for job in mdb.jobs.find():
            control_pid = job.get('control_pid')
            if ((control_pid is None or 
                not os.path.isdir('/proc/'+str(control_pid))) and
                job.get('status', '').startswith('running')):
                mdb.jobs.update({'_id': job['_id']},
                                {'$set': {
                            'status': \
                                'control process '+str(control_pid)+
                            ' disppeared without clearing up'}})
        print 'TESTLAUNCH: experiment override', dut_document.get('experiment')

        job = get_job(mdb, options.machine)
        if job:
            def update_job(field, value):
                """Update one field in job"""
                mdb.jobs.update({'_id':job['_id']}, 
                                {'$set': {field: value}})
            def set_status(status):
                """Update mongo status"""
                update_job('status', status)
            set_status('running')
            update_job('launch_time', time.time())
            update_job('control_pid', os.getpid())
            update_job('control_machine', gethostname())
            update_job('dut', options.machine)
            print 'I should run', job, 'on', options.machine
            command_line = list(job['command']) + [ '-m', options.machine]
            print 'running', command_line, 'with', job['timeout'], \
                'seconds timeout'
            def show(output):
                """show stderr"""
                for line in output.splitlines():
                    print line
                    make_log_entry(line, job_id=job['_id'],
                                   dut=options.machine)
            def finish(status, exc=None):
                """Mark test as finished"""
                set_status(status)
                if exc:
                    update_job('failure', str(exc))
                update_job('finish_time', time.time())
            try:
                run(command_line, timeout=job['timeout'],
                    output_callback=show, error_callback=show)
                finish('completed')
            except SubprocessError, exc:
                finish('failed (non zero exit code)', exc)
            except TimeoutError, exc:
                finish('failed (timed out)', exc)
            except Exception, exc:
                finish('internal failure', exc)
                update_job('failure', str(exc))
            print 'completed', command_line
            return

        if not (options.force or dut_document.get('run_bvt')):
            print 'TESTLAUNCH: BVT disabled for', options.machine
            exit(0)

        test_case, build = choose_test(
                options.machine, current_install=options.current_install,
                test_case_regexp = options.test_case_regexp)
        
        if options.pretend:
            return

        recording.set_description(test_case['description'])
        recording.set_build(build)
        print 'HEADLINE: started', recording.full_description(), 'on', gethostname()

        do_test(options.machine, test_case, str(build), recording.result_id,
                options.source_directory)
    finally:
        try:
            store_status_report(options.machine, reason='end of test')
        except Exception, exc:
            print 'HEADLINE: unable to store status report due to', exc

def get_version():
    """Return git version"""
    version =  run(['git', 'show'], cwd=abspath(split(__file__)[0]), 
                   word_split=True)[1]
    return version

def launch():
    """entry point"""
    parser = OptionParser()
    parser.add_option(
        '-m', '--machine',  metavar='MACHINE', action='store',
        help='Do test on MACHINE (e.g. kermit)')
    parser.add_option(
        '-f','--force', action = 'store_true',
        help='Do test even if automate not set to 1 in duts '
        'table of resultsdb')
    parser.add_option(
        '-q', '--quieter', action='store_true',
        help='Do not write stuff going through the log system to stdout')
    parser.add_option(
        '-c', '--current-install', action='store_true',
        help='Use the current install; do not install a more recent build')
    parser.add_option('-p', '--pretend', action='store_true',
                      help='Only work out what should be done; do not '
                      'touch machine')
    parser.add_option('-v', '--verbose', action='store_true',
                      help='Show all logging')
    parser.add_option('-l', '--loop', action='store_true',
                      help='Run repeatedly until we get an exception')
    parser.add_option('-r', '--resume', action='store_true',
                      help='In loop mode, resume after unhandled exception')
    parser.add_option('-g', '--disable-git-check', action='store_true',
                      help='Disable the git check that exits the loop when the '
                      'git version changes')
    parser.add_option('-t', '--test-case-regexp', action='store', 
                      metavar='REGEXP',
                      help='Run only test cases matching REGEXP')
    parser.add_option('-s', '--source-directory', action='store', 
                      metavar='DIRECTORY',
                      help='Assume extra source code for testing is '
                      'in DIRECTORY')
    options, args = parser.parse_args()
    if options.machine is None:
        if len(args) == 1:
            options.machine = args[0]
        else:
            print 'ERROR: machine not specified'
            print 'HINT: specify something like --machine fozzie'
            exit(1)
    mdb = mongodb.get_autotest()
    dutdoc = mdb.duts.find_one({'name':options.machine})
    if dutdoc is None:
        print 'ERROR: machine', dutdoc, 'not in database'
        print 'add it for instance by running experiments on it'
        exit(2)
    validate_dut_name(options.machine)

    if (dutdoc.get('run_bvt', 0) != 1 or
        dutdoc.get('control_machine') != gethostname()) and  not options.force:
        why = ''
        if dutdoc.get('run_bvt', 0) != 1:
            why += 'disabled '
        if dutdoc.get('control_machine') != gethostname():
            why += 'machine=='+ dutdoc.get('control_machine')
        print 'ERROR: automation for', options.machine, why
        print 'HINT: use --force to proceed anyway'
        exit(1)

    version = get_version()
    while 1:
        try:
            one_operation(options)
        except Exception:
            if options.resume:
                time.sleep(60)
            else:
                raise
        if not options.loop:
            break
        nversion = get_version()
        if version != nversion and not options.disable_git_check:
            print 'HEADLINE: git version changed from', version, 'to', nversion, 'so exiting test loop'
            break
        else:
            print 'INFO: still running', nversion

if __name__ == '__main__':
    launch()
