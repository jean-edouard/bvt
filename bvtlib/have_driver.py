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

"""Test if driver installed on Windows"""

from bvtlib.call_exec_daemon import call_exec_daemon, run_via_exec_daemon, \
    SubprocessError
from bvtlib.retry import retry

def have_driver(host, section, name):
    """Does host have driver name in section?"""
    try:
        def obtain():
            """Download devcon"""
            call_exec_daemon('unpackTarball', 
                             ['http://autotest.cam.xci-test.com/bin/devcon.tar.gz',
                              'C:\\'],
                             host=host)
        retry(obtain, 'download devcon', timeout=60)
        drivers = run_via_exec_daemon(['C:\\devcon\\i386\\devcon.exe', 
                                       'listclass', 
                                       section], timeout=60, host=host)
        print 'TOOLS: have',section, 'drivers', drivers
        print 'INFO:', 'found' if name in drivers else 'did not find', name
        return name in drivers
    except SubprocessError:
        pass
    return False
