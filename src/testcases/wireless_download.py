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

"""Connect to a known access point and download a file"""
from src.bvtlib.settings import NO_WIFI_MACHINES
from src.bvtlib.run import run, writefile

RUBY_SCRIPT = """
require 'dbus'

print 'hello world'
bus = DBus::SystemBus.instance

service = bus.service('org.freedesktop.NetworkManagerSystemSettings')
print 'service', service
nm = service.object('/org/freedesktop/NetworkManager')
print 'nm', nm
iface = nm["org.freedesktop.NetworkManager"]
print 'iface', iface
iface.GetDevices do |resp|
  puts "The response is #{resp}"
end
"""

FILENAME = '/go.rb'

def wireless_download(dut):
    """Main test entry point"""
    writefile(FILENAME, RUBY_SCRIPT, host=dut)
    out = run(['ruby', FILENAME], host=dut)
    print 'got', repr(out)

def entry_fn(dut):
    wireless_download(dut)

def desc():
    return 'Download content over specific wireless network'
