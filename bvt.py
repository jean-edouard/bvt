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

from optparse import OptionParser
from src.bvtlib.record_test import RecordTest
from src.bvtlib.console_logging import ConsoleMonitor
from src.bvtlib.stdout_filter import StdoutFilter
from sys import exc_info, exit
from pdb import post_mortem
from traceback import print_exc
from src.bvtlib.dhcp import get_addresses
import fcntl
import os
import time


class NodeAcquireException(Exception):
    """Something went wrong with node acquition"""


class NoValueForArgument(Exception):
    """We have no value for a test argument"""


class NoBuildFound(Exception):
    """Did not find suitable build in database"""


class InvalidNumberOfArgumentsException(Exception):
    """Did not provide the expected number of arguments"""


def list_test_cases(options):
    """Iterate over test cases directory and list available testcases
        for user."""
    file_list = []
    for subdir, dirs, files in os.walk("./src/testcases"):
        for f in files:
            if "__" not in f and "pyc" not in f:
                file_list.append(f)
    file_list.sort()
    for f in file_list:
        handle = __import__("src.testcases."+f.split('.')[0],
                            fromlist=["desc"])
        argcount = handle.entry_fn.func_code.co_argcount
        args = handle.entry_fn.func_code.co_varnames[:argcount]
        print f.split('.')[0] + "\n   >> " + "Desc: " + handle.desc() + \
            "\n   >> " + 'Args: %s' % (args,)


def construct_arg_dict(options, test_parameters, result_id, handle):
    """Work out test arguments given options, guest and test parameters.
    Also returns an expanded test_paramters"""

    argcount = handle.entry_fn.func_code.co_argcount
    args = handle.entry_fn.func_code.co_varnames[:argcount]
    arg_dict = {}

    if options.help:
        print handle.desc()
        print 'Expected arguments: %s' % (args,)
        exit()

    # Command line arguments should be general such as IP, MAC, build,
    # guest name, etc. --mode exists as a special instance for test cases.
    # Eg, the test soak.py will either set powerstate to s0 or s5; in that
    # context, mode can specify 'up' or 'down' to get the correct behavior.
    # Reduce need to make changes to bvt.py when new test cases are added.
    for arg in args:
        if arg == 'dut' and options.machine:
            arg_dict[arg] = options.machine
        elif arg == 'guest' and options.guest:
            arg_dict[arg] = options.guest
        elif arg == 'url' and options.url:
            arg_dict[arg] = options.url
        elif arg == 'build' and options.build:
            arg_dict[arg] = options.build
        elif arg == 'release' and options.release:
            arg_dict[arg] = options.release
        elif arg == 'mac_address' and options.mac_address:
            arg_dict[arg] = options.mac_address
        elif arg == 'result_id':
            arg_dict[arg] = result_id
        elif arg == 'vhd_name' and options.vhd_name:
            arg_dict[arg] = options.vhd_name
        elif arg == 'sync_name' and options.sync_name:
            arg_dict[arg] = options.sync_name
        elif arg == 'reboot_dur' and options.duration:
            arg_dict[arg] = options.duration
        elif arg == 'mode' and options.mode:
            arg_dict[arg] = options.mode
        elif arg == 'reason' and options.reason:
            arg_dict[arg] = options.reason
        elif arg == 'encrypt_vhd' and options.encrypt_vhd:
            arg_dict[arg] = True if options.encrypt_vhd == "True" else False

    if len(arg_dict) != handle.entry_fn.func_code.co_argcount:
        raise InvalidNumberOfArgumentsException()

    tpout = dict(test_parameters)
    tpout['description'] = handle.desc()
    print arg_dict
    return arg_dict, tpout


def execute_test(options, test_parameters, handle, n):
    try:
        with StdoutFilter(verbose=options.verbose) as logger:
            # XXX; we need to example arguments in test_case['description']
            # but do that in construct_arg_dict which requires result_id
            with RecordTest(record=options.record,
                            description=handle.desc(),
                            build=options.build,
                            dut=options.machine,
                            stdout_filter=logger) as recording:
                with ConsoleMonitor(options.machine, recording.result_id):
                    arg_dict, tps = construct_arg_dict(options,
                                                       test_parameters,
                                                       recording.result_id,
                                                       handle)
                    recording.set_description(tps['description'])
                    print tps['description']
                    # Support infinite looping of test if specified
                    if n == 'inf':
                        while 1:
                            handle.entry_fn(**arg_dict)
                    else:
                        for i in range(n):
                            handle.entry_fn(**arg_dict)

    except Exception, exc:
        if options.debugger_on_failure:
            print_exc()
            post_mortem(exc_info()[2])
        else:
            raise


def prep_test(options, testcase):
    test_parameters = {
        'dut': options.machine, 'record': options.record,
        'stash_guests': options.guest, 'verbose': options.verbose}
    handle = __import__("src.testcases." + testcase, fromlist=["entry_fn"])

    # When used with mongo for managing a testbed, mac address should be
    # determined automagically from machine name.
    if not options.mac_address:
        options.mac_address = get_addresses(options.machine)
    if options.iterations:
        n = int(options.iterations)
    elif options.loop:
        n = 'inf'
    else:
        n = 1
    execute_test(options, test_parameters, handle, n)


def bvt():
    """Run test cases"""
    usage = "usage: %prog [options] testcase"
    parser = OptionParser(add_help_option=False, usage=usage)

    # Test case options
    parser.add_option('-h', '--help', action='store_true',
                      help='Display usage information about a testcase.')
    parser.add_option('-v', '--verbose', action='store_true',
                      help='Show all logging on stdout')
    parser.add_option('-l', '--loop', action='store_true',
                      help='Repeat until failure')
    parser.add_option('-r', '--record', action='store_true',
                      help='Store records in database, default set to true')
    parser.add_option('-D', '--debugger-on-failure', action='store_true',
                      help="Start PDB if a test failure occurs")
    parser.add_option('-t', '--list-test-cases', action='store_true',
                      help='Print a list of all available test cases, '
                      'their descriptions, and args')
    parser.add_option('-m', '--machine',  metavar='MACHINE',
                      help='Do test on MACHINE (e.g. kermit)')
    parser.add_option('-a', '--mac-address', metavar='MAC_ADDRESS',
                      help='Target machine has MACADDRESS (for PXE installs')
    parser.add_option('-b', '--build', action='store',
                      help='Have --xen-client install BUILD', metavar='BUILD')
    parser.add_option('-g', '--guest', metavar='GUEST', action='store',
                      help='Test vm GUEST (e.g. win7 or vista or xp). '
                      'Optionally you may specify '
                      'a name for the VM like this win7:fish xp:soup.')
    parser.add_option('-c', '--iterations', metavar='NUMBER',
                      help='Stop test loop after NUMBER iterations')
    parser.add_option('-E', '--encrypt-vhd', action='store',
                      help='Create encrypted VHD files during OS '
                      'install from ISO')
    parser.add_option('-d', '--duration', action='store',
                      help='Duration to execute timed tests.')
    parser.add_option('-u', '--url', action='store', metavar='URL',
                      help='Use VHD from URL')
    parser.add_option('-n', '--vhd-name', action='store', metavar='VHDNAME',
                      help='Use this name for the VHD at the destination')
    parser.add_option('--mode', action='store',
                      help='Extra modifier for test cases. '
                      'Functionality varies from test to test.')
    parser.add_option('-R', '--reason',  action='store',
                      help='Provide a reason for performing the test.')
    options, args = parser.parse_args()
    if options.list_test_cases:
        list_test_cases(options)
        exit(0)
    if len(args) > 0:
        # Use dynamic module loading and introspection to invoke test cases and
        # ensure proper arguments are passed.
        prep_test(options, args[0])
    else:
        parser.print_help()

if __name__ == '__main__':
    bvt()
