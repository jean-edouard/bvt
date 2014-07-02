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

from bvtlib import store_artifact
from bvtlib.dbus_log_parser import parse_dbus_log, print_messages
from bvtlib.settings import ARTIFACTS_DBUS_SECTION

DBUS_LOG = '/var/log/dbus.log'
ALLOW_EAVESDROP = """
grep -L eavesdrop /etc/dbus-1/system.conf | xargs sed -i 's/context="default">/context="default">\\n    <allow eavesdrop="true"\/>/'
"""
KILL_DBUS_MONITOR = 'killall dbus-monitor'
DBUS_CMD = 'xec -s org.freedesktop.DBus '

GET_DBUS_OBSCURE_NAMES = """
xec -s org.freedesktop.DBus ListNames xargs echo | grep :
"""



def start_logging( dut):
    with connection.connect(host=dut, user='root') as sh_dut:
        print 'INFO:', 'kill old dbus monitors' 
        sh_dut.launch(KILL_DBUS_MONITOR)
        
        print 'INFO:', 'enable dbus eavesdrop' 
        sh_dut.launch(ALLOW_EAVESDROP)
        
        print 'INFO:', 'reload dbus config' 
        sh_dut.verified_launch(DBUS_CMD + 'ReloadConfig')
        
        print 'INFO:', 'start dbus logging' 
        sh_dut.verified_launch('dbus-monitor --system > %s&' % DBUS_LOG)



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

TEST_CASES = [
    { 'description' : 'Start logging dbus messages', 
      'trigger' : 'python ready',
      'options_predicate': lambda options: options.dbus_log_start, 
      'command_line_options': ['--dbus-log-start'],
      'function' : start_logging,  'arguments' : [('dut', '$(DUT)')]},
    { 'description' : 'Stop logging dbus messages', 'trigger' : 'python ready',
      'options_predicate': lambda options: options.dbus_log_stop, 
      'command_line_options': ['--dbus-log-stop'],
      'function' : stop_logging,  'arguments' : [('dut', '$(DUT)')]}]
