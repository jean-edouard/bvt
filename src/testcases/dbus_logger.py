#
# Copyright (c) 2011 Citrix Systems, Inc.
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

from os.path import join
from json import dumps

from src.bvtlib import store_artifact
from src.bvtlib.dbus_log_parser import parse_dbus_log, print_messages
from src.bvtlib.settings import ARTIFACTS_DBUS_SECTION
from src.bvtlib.run import run
DBUS_LOG = '/var/log/dbus.log'
ALLOW_EAVESDROP = """grep -L eavesdrop /etc/dbus-1/system.conf | xargs sed -i 's/context="default">/context="default"><allow eavesdrop="true"\/>/'
"""
KILL_DBUS_MONITOR = ['killall', 'dbus-monitor']
DBUS_CMD = ['xec', '-s', 'org.freedesktop.DBus ']

GET_DBUS_OBSCURE_NAMES = """
xec -s org.freedesktop.DBus ListNames xargs echo | grep :
"""

class InvalidArgumentException(Exception):
    """Invalid argument passed to function"""


def start_logging(dut):
    print 'INFO:', 'kill old dbus monitors'
    run(KILL_DBUS_MONITOR, host=dut) 
    
    print 'INFO:', 'enable dbus eavesdrop' 
    run(['echo "'+ALLOW_EAVESDROP+'" > /storage/eaves.sh'], host=dut, shell=True)
    run(['/storage/eaves.sh'], host=dut)
    
    print 'INFO:', 'reload dbus config' 
    run(DBUS_CMD+['ReloadConfig'], host=dut)

    print 'INFO:', 'start dbus logging' 
    run(['dbus-monitor', '--system', '>', '%s&'% DBUS_LOG], host=dut)

def stop_logging( dut):
    with connection.connect(host=dut, user='root') as sh_dut:
        print 'INFO:', 'kill dbus monitors' 
        sh_dut.launch(KILL_DBUS_MONITOR)
        log = sh_dut.read_file(DBUS_LOG)
        store_artifact.store_memory_artifact(log, ARTIFACTS_DBUS_SECTION, 
                                                   '.dbus.log')
        

        print 'INFO:', 'retrieve dbus names' 
        name_map = {}
        names,_ = sh_dut.verified_launch(GET_DBUS_OBSCURE_NAMES)
        for name in names.splitlines():
            has_owner,_ = sh_dut.verified_launch(DBUS_CMD + 'NameHasOwner %s' % name)
            if has_owner.strip() != 'true':
                continue
            pid,_ = sh_dut.verified_launch(DBUS_CMD + 'GetConnectionUnixProcessID %s' % name)
            rc, cmd, _ = sh_dut.launch('ps -p %s --no-headers -o %%c' % pid.strip())
            if rc == 0:
                name_map[name] = cmd.strip()

        store_artifact.store_memory_artifact(
            dumps(name_map), ARTIFACTS_DBUS_SECTION, '.dbus.map')
        print 'INFO:', 'parse dbus log' 
        print_messages(parse_dbus_log(log.splitlines()), known_agents=name_map)

def entry_fn(dut, mode):
    if mode == 'start':
        start_logging(dut)
    elif mode == 'stop':
        stop_logging(dut)
    else:
        raise InvalidArgumentException()
    

def desc():
    return 'Start logging dbus messages'
