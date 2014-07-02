#!/scratch/autotest_python/bin/python
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

from optparse import OptionParser
from bvtlib import test_names, test_cases, mongodb
from bvtlib.domains import find_domain, name_split, CannotFindDomain
from bvtlib.maybe import maybe
from bvtlib.validate_dut_name import validate_dut_name
from bvtlib.record_test import RecordTest
from bvtlib.settings import STATUS_REPORTS_ALWAYS, STATUS_REPORTS_NEVER
from bvtlib.run import run
from bvtlib.console_logging import ConsoleMonitor
from bvtlib.stdout_filter import StdoutFilter
from sys import exc_info
from random import choice
from pdb import post_mortem
from traceback import print_exc

from bvtlib import testGraph, testModules, testFinder
from time import sleep
import signal, subprocess
import os,sys
import string
import random

class NoValueForArgument(Exception):
    """We have no value for a test argument"""

def signal_handler(signal, frame):
    num = ':'.join(map(str,trace))
    print "key : ", testFinder.keyen(trace)
    sys.exit(0)

def set_experiment_install_flag(dut, value):
    """Set write flag for machine named dut"""
    mongodb.get_autotest().duts.update({'name':dut}, {'$set':{'write':value}})

def construct_arg_dict(options, guest, test_parameters, test_case, result_id):
    """Work out test arguments given options, guest and test parameters.
    Also returns an expanded test_paramters"""
    if guest is None: 
        os_name = 'dom0'
    else: 
        os_name, _ = name_split(guest)
        os_name = dict(test_names.ordering).get(os_name, os_name)

    options.caller = '1'
    if not options.vmlist:
        options.vmlist = 'all'

    specials = {
        '$(OS_NAME)' : os_name,
        '$(BUILD)' : options.build,
        '$(SOURCE_DIRECTORY)' :options.source_directory,
        '$(ENCRYPT_VHD)' : options.encrypt_vhd,
        '$(RESULT_ID)' : result_id,
        '$(GUEST)' : guest,
        '$(REBOOT)' : options.reboot,
        '$(DUT)' : options.machine,
        '$(TESTSTEPS)' : options.teststeps,
        '$(VMLIST)' : options.vmlist,
        '$(TESTPATH)' : options.testpath,
        '$(CALLER)' : options.caller }

    if options.machine:
        specials['$(DUT)'] = options.machine
    if options.soak_power_level:
        specials['$(SOAK_POWER_LEVEL)'] = choice(options.soak_power_level)
    if options.synchronizer_name:
        specials['$(SYNCHRONIZER_NAME)'] = options.synchronizer_name
    if options.xcbe_version:
        specials['$(XCBE_VERSION)'] = options.xcbe_version
    
    arg_dict = {}
    for name, value in test_case['arguments']:
        if type(value) == type('') and value.startswith('$('):
            if value in specials:
                ov = specials[value]
            else:
                raise NoValueForArgument(name, value)
        else:
            ov = value
        arg_dict[name] = specials.get(value, value)

    des = test_case['description']
    for specialk, value in specials.items():
        if value is not None:
            des = des.replace(specialk, str(value))
    tpout = dict(test_parameters)
    tpout['description'] = des
    for k in test_case:
        tpout.setdefault(k, test_case[k])
    return arg_dict, tpout

def run_test(test_parameters, test_case, options, guest=None):
    """Invoke test_callback described by test_case if it can run in the 
    context of options for guest"""
    optlist = test_case.get('command_line_options', []) + test_case.get(
        'store_list', [])
    if optlist:
        assert optlist[-1].startswith('--')
        optname = optlist[-1][2:].replace('-', '_')
        if not getattr(options, optname): 
            return

    pred = test_case.get('options_predicate')
    if pred and not pred(options): 
        return

    try:
        with StdoutFilter(verbose=options.verbose) as logger:
            with RecordTest(record=options.record,
                            description=test_case['description'], 
                            build=options.build, 
                            dut=options.machine,
                            stdout_filter=logger) as recording:
                with ConsoleMonitor(options.machine, recording.result_id):
                    arg_dict, tps = construct_arg_dict(options, guest, 
                                                       test_parameters, 
                                                       test_case, 
                                                       recording.result_id)
                    recording.set_description(tps['description'])
                    return test_case['function'](**arg_dict)
    except Exception, exc:
        if options.debugger_on_failure:
            print_exc()
            post_mortem(exc_info()[2])
        else:
            raise
    

def do_iteration(i, options):
    """Do one iteration of the test loop"""
    mdb = mongodb.get_autotest()
    set_experiment_install_flag(options.machine, 
                                (options.install_first or not 
                                 options.soak_power_level) and (i == 1))
    dutdoc = mdb.duts.find_one({'name':options.machine}) 
    write = (dutdoc if dutdoc else {}).get('write')
    test_parameters = {
        'dut':options.machine, 'record': options.record,
        'status_report_mode': STATUS_REPORTS_ALWAYS if 
         options.diagnostic_status_report else STATUS_REPORTS_NEVER,
        'stash_guests' : options.guest, 'verbose' : options.verbose,
        'stash_on_failure'  : options.stash_on_failure,
        'reinstall_on_failure' : options.reinstall_on_failure}
    def trigger_tests(condition, guest=None):
        """Trigger test cases matching condition for guest"""
        for test_case in test_cases.TEST_CASES:
            if test_case.get('trigger') == condition:
                run_test(test_parameters, test_case, options, guest)
    trigger_tests('first')        
    if write:
        trigger_tests('platform install')

    trigger_tests('build ready')
    trigger_tests('soakup')

#############
    x = 0
    trace = []

    if(not options.test_suite):
        signal.signal(signal.SIGINT, signal_handler)
        print 'Press Ctrl-C to stop'
        while(1):
            trace.append(x)                              #testFinder.getTag(x))
            trigger_tests(str(x))
            x = random.randint(1, 102)                   #testGraph.randF(x, 0)
    else:
        if mongodb.get_autotest().status.find_one({'name':options.machine}):
            print '\n\n','-'*10,'Found a saved test state for your machine, Do you want to continue','-'*10
            while 1:
                input = raw_input("yes/no: ")
                if input in 'yes':
                    break
                elif input in 'no':
                    return
            saved = mongodb.get_autotest().status.find_one({'name':options.machine},{'steps':1,'_id':0})
            list = saved['steps']
        else:
            list = testFinder.keyde(int(options.test_suite))
            print list
            mongodb.get_autotest().status.insert({'name':options.machine, 'steps':list})

        listTemp = list[:]
        for i in list:
            print "running test ",i
            trigger_tests(i)                             #testFinder.getkey(int(i)).func_name)
            listTemp.pop(0)
            mongodb.get_autotest().status.update({'name':options.machine},{'$set':{'steps':listTemp}})
        mongodb.get_autotest().status.remove({'name':options.machine})
############

    for guest in options.guest if options.guest else []:
        try:
            find_domain(options.machine, guest)
            have_domain = True
        except CannotFindDomain:
            have_domain = False
        print 'check for domain', guest, 'returned', have_domain
        write_guest = write or not have_domain
        if write_guest:
            trigger_tests('VM install', guest)
        domain = find_domain(options.machine, guest)
        if domain['status'] == 'stopped':
            run(['xec-vm', '-n', domain['name'], 'start'], 
                host=options.machine, timeout=600)
        if write_guest:
            trigger_tests('VM configure', guest)
            trigger_tests('VM accelerate', guest)
        trigger_tests('VM ready', guest)
    trigger_tests('soakdown')

def top_loop(options):
    """Run tests repeatedly"""
    set_experiment_install_flag(options.machine, 1)
    i = 0
    while True:
        i += 1
        okay, _ = maybe(lambda: do_iteration(i, options), 'launch test', verbose=False)
        set_experiment_install_flag(
            options.machine, 0 if (okay and options.soak_power_level) else 1)
        if options.loop_iterations is not None:
            if options.loop_iterations > i:
                break
        elif not options.loop:
            break
        print 'EXPERIMENTS: loop', i, options.loop_iterations, options.loop

def experiments():
    """Run test cases"""
    parser = OptionParser()
    parser.add_option(
        '-v', '--verbose', action='store_true',
        help='Show all logging on stdout')
    parser.add_option(
        '-m', '--machine',  metavar='MACHINE',
        help='Do test on MACHINE (e.g. kermit)')
    parser.add_option(
        '-g', '--guest', metavar='GUEST',action='append',
        help='Test vm GUEST (e.g. win7 or vista or xp). '
        'Optionally you may specify '
        'a name for the VM like this win7:fish xp:soup.')
    for test_case in test_cases.TEST_CASES:
        optlist = test_case.get('command_line_options')
        if optlist:
            parser.add_option(*optlist, **{'action' : 'store_true',
                                           'help':test_case['description']})
        store_list = test_case.get('store_list')
        if store_list:
            parser.add_option(*store_list, **{'action' : 'store',
                                           'help':test_case['description']})
            
    parser.add_option(
        '-b', '--build', action='store', 
        help='Have --xen-client install BUILD', metavar='BUILD')
    parser.add_option(
        '-B', '--branch', action='store', 
        help='Have --xen-client install BRANCH. Ignored if '
        'build specified with --build', 
        metavar='BRANCH')
    parser.add_option(
        '-n', '--network-test', action='store_true', 
        help='Do some quick network traffic tests')
    parser.add_option(
        '-l', '--loop', action='store_true', help='Repeat until failure')
    parser.add_option(
        '-c','--loop-iterations', metavar='NUMBER',
        help='Stop test loop after NUMBER iterations')
    parser.add_option(
        '--reboot', action='store', help='Enable reboot loop for N hours',
        metavar='N')
    parser.add_option(
        '--soak-power-level', action='append', metavar='LEVEL',
        help='Do soak test involving transition to LEVEL (e.g. s3)')
    parser.add_option(
        '--read-test', action='store_true',
        help='Do a read test when installing VHDs')
    parser.add_option(
        '--private', action='store_true', 
        help='Do not store result and logs in autotest databases [default!]')
    parser.add_option(
        '-r', '--record', action='store_true', help='Store records in database')
    parser.add_option(
        '--synchronizer-name', action='store',
        help='Name of Synchronizer host to run tests against')
    parser.add_option(
        '--xcbe-version', action='store',
        help='X-XCBE-version header to send to Synchronizer')
    parser.add_option('-S', '--stash-on-failure', action='store_true',
                      help='Stash away VHDs on failure')
    parser.add_option('-R', '--reinstall-on-failure', action='store_true',
                      help='Reinstall after stress test failures')
    parser.add_option('-F', '--install-first', action='store_true',
                      help='Install at start, even for stress tests. '
                      'For non-stress tests (i.e. -s not specified) this is '
                      'standard behaviour so this option has no effect.')
    parser.add_option('--do-not-detect-build', action='store_true',
                      help='Do not detect the build')
    parser.add_option('--xen-server', action='store', metavar='SERVER',
                      help='Activate xen server')
    parser.add_option('-s', '--source-directory', action='store', 
                      metavar='DIRECTORY',
                      help='Assume extra source code for testing is '
                      'in DIRECTORY')
    parser.add_option('-D', '--debugger-on-failure', action='store_true',
                      help="Start PDB if a test failure occurs")
    parser.add_option('-E', '--encrypt-vhd', action='store_true',
                      help='Create encrypted VHD files during OS '
                      'install from ISO')
    parser.add_option(
        '--ts', action='store', dest='test_suite',
        help='Runs a test suite')
    parser.add_option(
        '--vm', action='store', dest='vmlist',
        help='List of VMs under test')
    parser.add_option(
        '--block', action='store', dest='teststeps',
        help='List of test steps')
    parser.add_option(
        '--step', action='store', dest='testpath',
        help='Name of the step to be run for debugging')
    parser.add_option(
        '--build_list', action='store', dest='buildlist',
        help='Build from which upgrade needs to be done')
    parser.add_option(
        '--upgrade_to', action='store', dest='upgradeto',
        help='Build to which upgrade needs to be done')
    parser.add_option(
        '--list', action='store_true', help='Display test flow')
    parser.add_option(
        '--listall', action='store_true', help='Display test flow')
    parser.add_option(
        '--clean', action='store_true', help='Reset saved state of the test')
    parser.add_option(
        '--ff', action='store', dest='ff',
        help='Fast Forward')
    options, args = parser.parse_args()
    if args and options.machine is None:
        options.machine = args[0]
        args = args[1:]
    if options.build is None:
        branch = options.branch or 'master'
        query = {'branch':branch}
        if options.install_xen_client or options.upgrade_xt or \
                options.install_xt:
            build_doc = mongodb.get_autotest().builds.find_one(
                query,
                sort=[('build_time', mongodb.DESCENDING)])
            print 'HEADLINE: chose %(_id)s on %(branch)s' % build_doc
            options.build = str(build_doc['_id'])
            assert branch == build_doc['branch']
    
    if options.listall:
        count = mongodb.get_autotest().ts_cases.count()
        print count
        for i in range(1,count):
            temp = mongodb.get_autotest().ts_cases.find_one({'_id':str(i)})
            print temp
        return

    if options.test_suite:
            if not(options.testpath): options.testpath = 'all'
            #else:test_path = options.testpath
            if (options.test_suite == 'list'):
                print '='*90
                print "Avaliable test suits are"
                print '-'*90
                print " install                      :- Installs build, VM and XC tools"
                print " upgrade                      :- Tests XC upgrade"
                print " smoke                        :- Smoke tests (only power operations)"
                print " lifecycle_win7x64_install    :- VM lifecycle install tests for Win7x64"
                print " lifecycle_win7x64_powerops   :- VM lifecycle power tests on Win7x64"
                print " lifecycle_win7x32_install    :- VM lifecycle install tests for Win7x32"
                print " lifecycle_win7x32_powerops   :- VM lifecycle power tests on Win7x32"
                print " lifecycle_vista_install      :- VM lifecycle install tests for Vista"
                print " lifecycle_vista_powerops     :- VM lifecycle power tests on Vista"
                print " lifecycle_xp_install         :- VM lifecycle install tests for XP"
                print " lifecycle_xp_powerops        :- VM lifecycle power tests on XP"
                print " power_management             :- Power management test cases"
                print " gruboptions                  :- Tests different grub options"
                print "\n XT Test cases"
                print '-'*90
                print " XT-ALL                       :- Run all test cases(excluding XT-install)"
                print " XT-install                   :- Install VM on encrypted VHD"
                print " XT-TPM                       :- TPM test cases"
                print " XT-selinux                   :- Selinux test cases"
                print " XT-autoboot                  :- Setting VM autoboot"
                print " XT-audio                     :- Audio policies"
                print " XT-USB                       :- USB pass through"
                print " XT-policies                  :- XT policies"
                print " XT-resetOnBoot               :- Reset VM on boot"
                print " XT-nilfvm                    :- NILFVM testcases"
                print " XT-viptables                 :- vip tables"
                print " XT-attach-stubdom            :- Attach stubdom to test VM"
                print " XT-detach-stubdom            :- Detach stubdom from test VM"
                print " XT-powerops                  :- Host SVM power operations"
                print " XT-3Dpowerops                :- Host PVM power operations"
                print '.'*90
                print "steps :--- Run with --block <x,y> to block steps x & y"
                print " vm_force_shutdown, vm_hibernate, vm_shutdown, vm_sleep, vm_reboot"
                print " host_hibernate, host_sleep, host_reboot, host_shutdown"
                print '='*90
                return

            elif options.test_suite == 'install':
                options.test_suite = '1002003'

            elif options.test_suite == 'upgrade':
                print "Tests are not ready, Exiting..."
                return

            elif options.test_suite == 'smoke':
                options.test_suite = '004005006007008009010011012013014015016'

            elif options.test_suite == 'lifecycle_win7x64_install':
                options.test_suite = '020021'

            elif options.test_suite == 'lifecycle_win7x64_powerops':
                options.test_suite = '023024025026027028029030031032033034'

            elif options.test_suite == 'lifecycle_win7x32_install':
                options.test_suite = '036037'

            elif options.test_suite == 'lifecycle_win7x32_powerops':
                options.test_suite = '038040041042043044045046047048049050'

            elif options.test_suite == 'lifecycle_vista_install':
                options.test_suite = '054055'

            elif options.test_suite == 'lifecycle_vista_powerops':
                options.test_suite = '056057058059060061062063064065066067068'

            elif options.test_suite == 'lifecycle_xp_install':
                options.test_suite = '072073'

            elif options.test_suite == 'lifecycle_xp_powerops':
                options.test_suite = '074075076077078079080081082083084085086'

            elif options.test_suite == 'power_management':
                options.test_suite = '089090091092093094095096097098099100101102'

            elif options.test_suite == 'gruboptions':
                print "Tests are not ready, Exiting..."
                return
###XT#
            elif options.test_suite == 'XT-install':
                options.test_suite = '104'

            elif options.test_suite == 'XT-TPM':
                options.test_suite = '106107108'

            elif options.test_suite == 'XT-selinux':
                options.test_suite = '112113'

            elif options.test_suite == 'XT-autoboot':
                options.test_suite = '115'

            elif options.test_suite == 'XT-audio':
                options.test_suite = '118117'

            elif options.test_suite == 'XT-USB':
                options.test_suite = '119'

            elif options.test_suite == 'XT-policies':
                options.test_suite = '120'

            elif options.test_suite == 'XT-resetOnBoot':
                options.test_suite = '122'

            elif options.test_suite == 'XT-nilfvm':
                options.test_suite = '125127'

            elif options.test_suite == 'XT-viptables':
                options.test_suite = '129130'

            elif options.test_suite == 'XT-attach-stubdom':
                options.test_suite = '131'

            elif options.test_suite == 'XT-powerops':
                options.test_suite = '109'

            elif options.test_suite == 'XT-3Dpowerops':
                options.test_suite = '110'

            elif options.test_suite == 'XT-detach-stubdom':
                options.test_suite = '132'
###XT#

            elif int(options.test_suite) not in range(1,800):
                print "**** Test suite does not exist ****"

    if options.clean:
        mongodb.get_autotest().status.remove({'name':options.machine})
        return

    if options.ff:
        saved = mongodb.get_autotest().status.find_one({'name':options.machine},{'steps':1,'_id':0})
        if saved: list = saved['steps']
        else:
            list = testFinder.keyde(int(options.test_suite))
            mongodb.get_autotest().status.insert({'name':options.machine, 'steps':list})
        for j in range(0, int(options.ff)):
            list.pop(0)
        mongodb.get_autotest().status.update({'name':options.machine},{'$set':{'steps':list}})
        return

    if options.list:
        saved = mongodb.get_autotest().status.find_one({'name':options.machine},{'steps':1,'_id':0})
        if saved: list = saved['steps']
        else: list = testFinder.keyde(int(options.test_suite))
        for i in list:
            temp = mongodb.get_autotest().ts_cases.find_one({'_id':i})
            print temp['description']
        return

    os.system('ssh-copy-id -i /root/.ssh/id_rsa.pub '+options.machine)

    if args and options.machine is None:
        options.machine = args[0]
        args = args[1:]

    if options.teststeps is None:
        options.teststeps = 'nil'

    if options.machine:
        validate_dut_name(options.machine)
    top_loop(options)

if __name__ == '__main__': 
    experiments()
