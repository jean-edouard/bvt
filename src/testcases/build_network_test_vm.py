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

"""Build Network test VM from scratch"""
from src.testcases.install_guest import install_guest
from src.testcases.install_tools import install_tools
from src.bvtlib.run import run
from src.bvtlib.domains import domain_address
from src.bvtlib.linux_guest import create_file
from src.bvtlib.domains import name_split

BASE_OS = 'ubuntu12.04.2x64'
NETWORK_TEST_OS_NAME = 'ubuntunettest'

SSHV4V_UPSTART_PATH = '/etc/init/ssh_v4v.conf'
SSHV4V_UPSTART_CONTENT = """
# ssh_v4v - OpenBSD Secure Shell server over v4v
#
# The OpenSSH server provides secure shell access to the system.

description     "OpenSSH server over v4v"

start on filesystem or runlevel [2345]
stop on runlevel [!2345]

env LD_PRELOAD="/usr/lib/libv4v.so"
env INET_IS_V4V="1"
export LD_PRELOAD
export INET_IS_V4V

respawn
respawn limit 10 5
umask 022

# 'sshd -D' leaks stderr and confuses things in conjunction with 'console log'
console none

pre-start script
    test -x /usr/sbin/sshd || { stop; exit 0; }
    test -e /etc/ssh/sshd_not_to_be_run && { stop; exit 0; }
    test -c /dev/null || { stop; exit 0; }

    mkdir -p -m0755 /var/run/sshd
end script

# if you used to set SSHD_OPTS in /etc/default/ssh, you can change the
# 'exec' line here instead
exec /usr/sbin/sshd -D -o PidFile=/var/run/sshd_v4v.pid -o Port=2222
"""

def install_net_utils(host):
    pass

def configure_sshv4v(host):
    create_file(host, SSHV4V_UPSTART_PATH, SSHV4V_UPSTART_CONTENT) 

def build_network_test_vm(dut, name=NETWORK_TEST_OS_NAME):
    print 'HEADLINE: building network test vm from scratch'
    guest_name = "%s:%s" % (BASE_OS, name) 
    install_guest(dut, guest=guest_name, kind='iso')
    install_tools(dut, name)
    vm_address = domain_address(dut, name)
    install_net_utils(vm_address)
    configure_sshv4v(vm_address)
    

def entry_fn(dut):
    build_network_test_vm(dut)

def desc():
    return 'Build network test VM from scratch'

