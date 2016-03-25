#!/usr/bin/python
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

import sys
import time
import os
import string
import pymongo
import shutil
import fcntl
import traceback
from optparse import OptionParser
from sys import exit
from src.bvtlib import mongodb
from src.bvtlib.time_limit import TimeoutError
from src.bvtlib.run import run, SubprocessError
from src.bvtlib.console_logging import ConsoleMonitor
from src.bvtlib.stdout_filter import StdoutFilter
from src.bvtlib.record_test import RecordTest
from src.bvtlib.settings import BUILDBOT2_ALL_BUILDERS_URL,\
    BUILDBOT2_BUILDER_URL, BUILD_SERVERS, TEST_NODES, BUILDBOT_BUILD_SERVERS,\
    RESULTS_RECIPIENTS
from src.bvtlib.email_results import ResultMailer
from re import match
from os.path import split
from time import sleep
from multiprocessing import Process
from bson import objectid
from json import loads
from urllib import urlopen
from subprocess import call


lockpts = []


class SuiteFailedException(Exception):
    """Test Suite failed."""


class NodeAcquireException(Exception):
    """Unable to acquire a node for testing."""


class NoMatchingBuilds(Exception):
    """No builds on required branch"""


class NoMatchingTests(Exception):
    """No tests are possible in this configuration"""


def send_mail(options, mdb, recording, suite):
    """Send an email to designated recipients containing information about
        the completed test."""
    try:
        mailer = ResultMailer(RESULTS_RECIPIENTS)
        suite_results = mdb.suiteresults.find_one(
                     {'result_id': recording.result_id, 'suite': suite})
        build_info = {'build': options.build, 'node': options.machine,
                      'result_id': recording.result_id}
        mailer.format_message(suite_results, build_info)
        mailer.send()
    except Exception:
        print 'INFO: Trouble mailing test results.'
        print 'INFO: Check your mailutils and postfix configuration.'
        pass


def ex_handler(message, code):
    print message
    if sys.exc_info()[0] is not None:
        print sys.exc_info()
        print traceback.format_exc()
    sys.exit(code)


def set_latest_successful_build(options, dut):
    """Legacy functionality to select the latest successful build if
        one is not specified.  Not currently used."""
    mdb = mongodb.get_autotest()
    cur = mdb.builds.find(sort=[("build_time", pymongo.DESCENDING)])
    for build in cur:
        print build
        name = build['builderName']
        if 'failure' not in build:
            options.build = build['id']
    if options.build is None:
        ex_handler('No successful builds available on any builder.', 4)


def set_build_path(options, dut):
    """Determine the location of the build to test.  If remote,
        retrieve build. Update mongo DUT to include name of build."""
    mdb = mongodb.get_autotest()
    server_set = False
    for server in BUILD_SERVERS:
        try:
            run("lftp -c mirror -x index.html* -x logs/ -x iso/ \
                -x raw/ -x packages/ -x git_heads -x sdk/ --parallel=4 \
                --only-missing {0}/{1} /builds/{1}\
                ".format(server, options.build), shell=True, timeout=3600)
            mdb.duts.update({'name': dut},
                            {'$set': {'build': '/builds/'+options.build}})
            server_set = True
        except Exception:
            print 'INFO: Build not found on server, continuing.'
    if not server_set and options.server:
        # Server is not the upstream build server target,
        # must follow convention Create a user autotest on your server,
        # add its public ssh key to authorized_keys? Place your build
        # tree in /home/autotest/builds/ Build tree should have the output
        # format of an openxt build. Test connection to server first so we
        # can timeout quickly.
        run(['ssh', '-i', '/home/user/keys/id_rsa',
             'autotest@%s' % options.server, 'uptime'])
        run(['rsync', '-arue', "ssh -i /home/user/keys/id_rsa",
             '--exclude=logs',
             '--exclude=raw',
             '--exclude=packages',
             '--exclude=iso',
             '--exclude=git_heads',
             '--exclude=sdk',
             'autotest@%s:~/builds/' % options.server + options.build,
             '/builds/'], timeout=3600)
        mdb.duts.update({'name': dut},
                        {'$set': {'build': '/builds/'+options.build}})
    if os.path.exists(options.build):
        mdb.duts.update({'name': dut},
                        {'$set': {'build': options.build}})
        server_set = True
    else:
        mdb.duts.update({'name': dut}, {'$set': {'build': 'Unknown'}})


def suite_operation(options, ip):
    """Execute a series of test suites, recording stdout and stderr
        for each.  Record failure or success and update mongo accordingly."""
    options.machine = ip
    try:
        with StdoutFilter(verbose=options.verbose) as recording:
            with RecordTest(record=True, dut=options.machine,
                            description=str(options.suites),
                            stdout_filter=recording,
                            job_id=options.job) as recording:
                with ConsoleMonitor(options.machine, recording.result_id):
                    for suite in options.suites:
                        do_test_suite(options, recording, suite)
    except SuiteFailedException as ex:
        ex_handler('Suite failed exception triggered', 7)


# Instead of queueing jobs, which are modified during/after test completes,
# Maintain a list of suites in mongodb that can be invoked on a test machine
# Suites should contain some sequence of related test cases.
#
# 'name':'install-suite'
# 'steps':2
# 's-1':['./bvt.py','pxe_install_xc']
# 's-2':['./bvt.py','check_mounts']
def do_test_suite(ops, recording, suite):
    """Execute a single test suite by running each step listed sequentially.
        Record failures and throw execeptions.  If a step fails, suite will
        continue if step was not critical (such as build installation)."""
    try:
        mdb = mongodb.get_autotest()
        dut_document = mdb.duts.find_one({'name': ops.machine})
        suitedoc = mdb.suites.find_one({'name': suite})
        recording.gen_suite_log(suite, suitedoc['steps'])
        installer_error = False

        def show(output):
            for line in output.splitlines():
                print line

        for i in range(suitedoc['steps']):
            cmd_line = list(suitedoc['s-'+str(i)]) + ['-m', ops.machine]
            cmd_line += ['-b', '/builds/'+ops.build] if ops.build else []
            try:
                # Timeout should be a better calculated value.
                print 'Starting Step'
                recording.step_start(suite, i)
                print 'INFO: Command: ', cmd_line
                run(cmd_line, timeout=7200, output_callback=show,
                    error_callback=show)
                print 'INFO: completed step ', i
                recording.update_step(suite, i, 'PASS')
            except Exception, exc:
                if "pxe_install_xc" in string.join(cmd_line):
                    print 'ERR: Install failed, stop remaining tests.'
                    installer_error = True
                print 'ERR: Test failure', exc
                recording.update_step(suite, i, 'FAIL',
                                      reason=repr(sys.exc_info()[0]))
                if installer_error:
                    break
            print 'Sleeping between steps.'
            sleep(5)

    finally:
        print 'INFO: Logging test suite outcome.'
        fail = False
        suite_results = mdb.suiteresults.find_one(
                        {'result_id': recording.result_id, 'suite': suite})
        num_steps = suite_results['steps']
        if installer_error:
            print 'INFO: Suite Failed, installer error. \
                   Stopping all further tests.'
            recording.update_suite(suite, 'FAIL',
                                   reason=repr(sys.exc_info()[1]))
            recording.failed = True
        for i in range(num_steps):
            if 'step'+str(i) in suite_results.keys():
                if suite_results['step'+str(i)] == 'FAIL':
                    fail = True
            else:
                fail = True
        if fail:
            print 'INFO: Suite Failed.'
            recording.update_suite(suite, 'FAIL',
                                   reason=repr(sys.exc_info()[1]))
            recording.failed = True
            send_mail(ops, mdb, recording, suite)
            raise SuiteFailedException()
        else:
            print 'INFO: Suite passed.'
            recording.update_suite(suite, 'PASS')
            send_mail(ops, mdb, recording, suite)


def acquire_nodes(num_nodes):
    if(num_nodes > TEST_NODES):
        raise NodeAcquireException()
    nodes = []
    for i in range(TEST_NODES):
        if len(nodes) == num_nodes:
            break
        f = open('nodes/node'+str(i), "w")
        lockpts.append(f)
        try:
            fcntl.flock(lockpts[i], fcntl.LOCK_EX | fcntl.LOCK_NB)
            nodes.append(i)
        except (IOError):
            print 'Node %d locked.' % i
            pass
    if len(nodes) == 0:
        return None
    return nodes


def dut_free(num):
    f = open('nodes/node'+str(num))
    lockpts.append(f)
    try:
        fcntl.flock(lockpts[0], fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except (IOError):
        print 'Node %d locked.' % dut
        return False


def suite_callback(option, opt, value, parser):
    setattr(parser.values, option.dest, value.split(','))


def verify_args(options):
    """Do error checking on arguments passed into autolaunch"""

    if options.build is None:
        print "WARN: No build specified.  This will break testcases \
                requiring a build option such as pxe_install_xc."

    if options.server is None:
        print "WARN: No build server specified.  This will break \
                testcases requiring a server to pull builds from, \
                such as pxe_install_xc."

    if options.server and options.build is None:
        ex_hander('ERR: Build server specified but no build provided.', 4)

    if options.machine and options.nodes:
        ex_handler('ERR: Use of both -m and -n together is prohibited.', 8)


def launch():
    """entry point"""
    thr = []
    test_nodes = None
    proc_err = False
    parser = OptionParser()
    parser.add_option(
        '-m', '--machine',  metavar='MACHINE', action='store',
        help='Do test on MACHINE (e.g. kermit)')
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
    parser.add_option('-r', '--resume', action='store_true',
                      help='In loop mode, resume after unhandled exception')
    parser.add_option('-g', '--disable-git-check', action='store_true',
                      help='Disable the git check that exits the loop when the'
                      ' git version changes')
    parser.add_option('-t', '--test-case-regexp', action='store',
                      metavar='REGEXP',
                      help='Run only test cases matching REGEXP')
    parser.add_option('-S', '--suites', action='callback',
                      callback=suite_callback,
                      metavar='SUITES', type='string',
                      help='We should do automated testing for testsuite.')
    parser.add_option('-n', '--nodes', action='store',
                      metavar='NODES',
                      help='Use n test nodes for automated testing.')
    parser.add_option('-b', '--build', action='store',
                      metavar='BUILD',
                      help='Buildername and buildnumber')
    parser.add_option('-s', '--server', action='store',
                      metavar='SERVER',
                      help='Specify the buildserver to pull build from.\
                            Librext does not use\
                            buildername/number convention for --build option.')
    parser.add_option('-j', '--job', action='store', metavar='JOB',
                      help='Job ID associated with this instance of autolaunch. \
                            Purely administrative.')
    parser.add_option('-d', '--device', action='store',
                      metavar='DEVICE',
                      help='Acquire a specific node to run tests on,\
                            provided it is free.')

    options, args = parser.parse_args()
    mdb = mongodb.get_autotest()

    def update_dut(num, field, value):
        """Update mongo entry for dut"""
        mdb.duts.update({'num': num},
                        {'$set': {field: value}})

    def release_nodes():
        """Release 'acquired' field on each dut regardless
            of success or failure"""
        if options.nodes:
            for i in test_nodes:
                update_dut(i, "acquired", 0)
        elif options.machine:
            dut_doc = mdb.duts.find_one({'name': options.machine})
            update_dut(dut_doc['num'], "acquired", 0)

    verify_args(options)
    try:
        if options.machine:
            dut_doc = mdb.duts.find_one({'name': options.machine})
            if dut_free(dut_doc['num']):            
                test_nodes = [dut_doc['num']]
        if options.nodes:
            test_nodes = acquire_nodes(int(options.nodes))
        if test_nodes is None:
            ex_handler('No available nodes.', 3)

        # returns a list of available nodes. use to index directly.
        for n in test_nodes:
            node = mdb.duts.find_one({'num': n})
            if node is None:
                ex_handler('Test node does not exist in pool,\
                            check mongo configuration.', 9)
            update_dut(node['name'], "acquired", 1)
            print "INFO: Running tests %s running on node %s" \
                  % (options.suites, n)
            dutdoc = mdb.duts.find_one({'name': node['name']})
            if options.build is not None:
                set_build_path(options, node['name'])
            thr.append(Process(target=suite_operation,
                       args=(options, node['name'])))
    except Exception:
        release_nodes()
        ex_handler('ERR: Internal error.', 6)

    # We're good to go, start the threads.
    for p in thr:
        p.start()
    for p in thr:
        p.join()
        if p.exitcode != 0:
            proc_err = True

    release_nodes()
    if proc_err:
        ex_handler('ERR: Error occurred on test node.', 7)

if __name__ == '__main__':
    launch()
