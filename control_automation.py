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

"""Command line interface to control automation column of duts colletion"""
import optparse, sys, socket
from bvtlib import mongodb
from bvtlib.run import run
from socket import gethostname
from os import getpid, getuid
from time import localtime, time, asctime
from getpass import getuser
from subprocess import call
from bvtlib.set_pxe_build import set_pxe_build


def control_automation(machines, automate=1):
    """Implement automation changes"""
    mongo = mongodb.get_autotest()
    for host in machines:
        existing = mongo.duts.find_one({'name':host})
        set_update = {'run_bvt':1}
        if existing is None or existing.get('control_machine') is None:
            set_update['control_machine'] = socket.gethostname()
        update = {'$set': set_update} if automate else {
            '$unset': {'run_bvt':True}}
        if existing is None:
            mongo.duts.insert({'name':host})
        mongo.dut_changes.save( 
            {'dut':host, 'hostname':gethostname(), 'user': getuser(),
             'uid': getuid(),
             'epoch': time(), 'localtime':asctime(localtime()),
             'dut_record_before': mongo.duts.find_one({'name':host}),
             'pid': getpid(), 'run_bvt':1 if automate else 0})
        mongo.duts.update({'name':host}, update, upsert=True)
        if not automate:
            print 'cleared PXE automation for', host
            set_pxe_build(host, action='boot')
        else:
            print 'leaving PXE automation for', host, 'alone'

def main():
    """implement CLI"""
    parser = optparse.OptionParser()
    parser.add_option(
        '-e', '--enable', action='store_true',
        help='Enable BVT automation for machines')
    parser.add_option(
        '-d', '--disable', action='store_true',
        help='Disable BVT automation for machines')
    options, args = parser.parse_args()
    mdb = mongodb.get_autotest()
    if not (options.enable or options.disable):
        if options.update == []:
            print 'Example commands:'
            for row in mdb.duts.find():
                print '\tcontrol_automation',
                print ('--disable' if row.get('run_bvt') else '--enable'),
                print row['name'],
                if row.get('run_bvt'):
                    print ' # BVT controlled by', row['control_machine'],
                else:
                    print ' # (automation disabled)',
                print 
            sys.exit(1)
        else:
            sys.exit(0)
    if options.enable and options.disable:
        print 'ERROR: do not specify --enable and --disable'
        sys.exit(2)
    if len(args) == 0:
        print 'ERROR: specify at least one machine as an argument'
    machines = []
    for arg in args:
        exitcode = call(['host', arg])
        if exitcode != 0:
            print 'ERROR: no DNS record for host name', arg
            sys.exit(4)
    mongo = mongodb.get_autotest()
    for arg in args:
        if mongo.duts.find_one({'name':arg}) is None:
            print 'ERROR: no such machine', arg
        else: machines.append( (arg))
    if len(machines) != len(args): 
        sys.exit(3)
    control_automation(machines, options.enable)


if __name__ == '__main__': 
    main()
    
