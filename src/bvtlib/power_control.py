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

"""Control power state of test machines"""

from src.bvtlib.settings import DEFAULT_POWER_CONTROL, AMTTOOL, AMTENV
from src.bvtlib.mongodb import get_autotest
from src.bvtlib.database_cursor import open_database
from src.bvtlib.time_limit import time_limit
from time import sleep
from src.bvtlib.run import run
from src.bvtlib.wait_to_come_up import wait_to_come_up, wait_to_go_down
from src.bvtlib.retry import retry
from src.bvtlib import call_exec_daemon, wait_for_windows, domains
from src.bvtlib.snmp_apc import PDU
from re import match
from src.bvtlib.mongodb import NoMongoHost

class NoPowerControl(Exception): 
    """No power control is defined for DUT"""

class UnknownMachine(Exception):
    """Unknown machine"""

class UnexpectedPowerState(Exception):
    """Power state is not as expected"""

class UnableToObtainPowerState(Exception):
    """No method for obtaining power state on dut worked"""

PDUs = {}

def get_PDU(ipaddr):
    if ipaddr not in PDUs:
        PDUs[ipaddr] = PDU(ipaddr)
    return PDUs[ipaddr]

def get_power_control_type(dut):
    """Get power control type for dut"""
    if dut == 'blinkenlights':  # for debugging, without having to define a spurious semihost in the hosts table
        return 'snmp-apc:flipper:8'
    mdb = get_autotest()
    dutdoc = mdb.duts.find_one({'name':dut})
    if dutdoc is None:
        raise UnknownMachine(dut)
    if dutdoc.get('power_control') is None:
        mdb.duts.update(
            {'name':dut}, {'$set':{'power_control': DEFAULT_POWER_CONTROL}}, 
            upset=True)
        dutdoc = mdb.duts.find_one({'name':dut})
    return dutdoc['power_control']

def set_power_state(dut, state, args):
    """Set AMT state"""
    try:
        pcontrol = get_power_control_type(dut)
    except NoMongoHost:
        pcontrol = 'AMT'
    print 'INFO: ', pcontrol
    APC_match = match('snmp-apc:(.+?):(.+)', pcontrol)
    if APC_match is not None:
        switcher = APC_match.group(1)
        host = int(APC_match.group(2))
        pdu = get_PDU(switcher)
        outlet = pdu.get_outlet_by_number(host)
        if state == 's5':
            outlet.off()
        else:
            outlet.on()
    elif pcontrol == 'AMT':
        #Wake machine out of M-Off state if idle timer was reached.
        run([AMTTOOL, dut+'-amt'], env=AMTENV, timeout=60, stdin_push='y\n')
        sleep(5)
        run([AMTTOOL, dut+'-amt']+args, env=AMTENV, timeout=60, stdin_push='y\n')
        sleep(5)
        verify_power_state(dut, state)
    elif pcontrol.startswith('franken'):
        run([('/bvt-device/hard_turn_off.pl' if state == 's5' else 
             '/bvt-device/turn_on.pl'), pcontrol[-1]], 
            host='igor.cam.xci-test.com', cwd='/bvt-device')
    elif pcontrol == 'statedb':
        sdb = open_database('statedb')
        config = open_database('configdb')
        asset = open_database('assetdb').select1_field(
            'tag', 'assets', name=dut)
        if 0:
            # sometimes (e.g. fozzie in July 2011)
            asset2 = config.select1_field('asset', 'ips', 
                                          reverse_dns=dut+'.cam.xci-test.com')
            print 'from configdb', asset2
            print 'from assetdb', asset
            assert asset == asset2

        with time_limit(300, description='set power state'):
            while 1:
                current = sdb.select1_field('current_power', 'control', 
                                            asset=asset)
                print 'POWER_CONTROL: statedb reports power state', current, \
                    'for', dut, asset,
                statep = 's1' if state == 's0' else state
                if current == statep:
                    print '... happy'
                    break
                sdb.execute('UPDATE control SET desired_power=%s '
                            'WHERE asset=%s', (statep, asset))
                print '... requesting', statep
                sleep(2)
    else:                       # grrr: no "if (a=foo()) bar(a);" in python!
        raise NoPowerControl(dut, pcontrol, state)

def set_s5(dut):
    """Set dut to s5"""
    set_power_state(dut, 's5', ['powerdown'])

def set_s0(dut):
    """Set dut to s0"""
    set_power_state(dut, 's0', ['powerup'])

def set_pxe_s0(dut):
    """Set dut to s0 and PXE"""
    set_power_state(dut, 's0', ['powerup', 'pxe'])

def power_cycle(dut, pace=5, pxe=False):
    """Powercycle dut"""
    try:
        set_s5(dut)
        print 'POWER: set power state s5 for', dut
        print 'POWER: waiting', pace, 'seconds'

        sleep(pace)
        if pxe:
            set_pxe_s0(dut)
        else:
            set_s0(dut)
        print 'POWER: set power state s0 for', dut
    except NoPowerControl:
        print 
        print
        print '!!! please make', dut, 'PXE boot then press return!!!'
        raw_input()
        print '!!! OKAY, proceeding'

def get_power_state(dut):
    """Return power state of dut"""
    pcontrol = get_power_control_type(dut)
    APC_match = match('snmp-apc:(.+?):(.+)', pcontrol)
    if APC_match is not None:
        switcher_name = APC_match.group(1)
        outlet_number = int(APC_match.group(2))
        pdu = get_PDU(switcher_name)
        outlet = pdu.get_outlet_by_number(outlet_number)
        return 's0' if outlet.status() else 's5'
    elif pcontrol == 'AMT':
        out = run([AMTTOOL, dut+'-amt'], env=AMTENV)
        for state in ['s0', 's1', 's2', 's3', 's4', 's5', 's6']:
            if 'Powerstate:   '+state.upper() in out:
                print 'POWER: found', dut, 'in power state', state, \
                    'according to AMT'
                return state
    else:                       # grrr: no "if (a=foo()) bar(a);" in python!
        raise UnableToObtainPowerState(dut, pcontrol)

def verify_power_state(dut, state):
    """Check that dut is in state. If not, throw UnexpectedPowerState"""
    actual = get_power_state(dut)
    if actual != state:
        raise UnexpectedPowerState(dut, 'want=%s have=%s' % (state, actual))

def platform_transition(dut, verb):
    """Perform verb on dut"""
    srv ='com.citrix.xenclient.xenmgr'
    obj ='/host'
    intf='com.citrix.xenclient.xenmgr.host'
    run(['xec', '-s', srv, '-o', obj, '-i', intf, verb], host=dut, wait=False)

def reboot(dut, timeout=600, managed=True):
    """Reboot dut by running shutdown, and wait for it to come back"""
    if managed:
        platform_transition(dut, 'reboot')
    else:
        run(['shutdown', '-nr', 'now'], host=dut, wait=False)
    wait_to_go_down(dut)
    wait_to_come_up(dut)

def xenmgr_sleep(dut):
    """Tell xenmgr to make the platform sleep and wait until it does"""
    platform_transition(dut, 'sleep')
    wait_to_go_down(dut, timeout=15)

def xenmgr_shutdown(dut):
    """Tell xenmgr to make the platform shutdown and wait until it does"""
    platform_transition(dut, 'shutdown')
    wait_to_go_down(dut)

def xenmgr_hibernate(dut):
    """Tell xenmgr to make the platform hibernate and wait until it does"""
    platform_transition(dut, 'hibernate')
    wait_to_go_down(dut)

def kernel_sleep(dut):
    """Tell linux kernel to make dut sleep"""
    run(['sh', '-c', 'echo -n mem > /sys/power/state'], dut=dut)

