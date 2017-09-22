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

"""Install the latest release and then upgrade it to the current build"""

from src.testcases.pxe_install_xc import pxe_install_xc
from src.bvtlib.settings import CUSTOM_WALLPAPER
from src.testcases.ensure import ensure
from src.bvtlib.domains import find_domain
from src.bvtlib.run import run

class SettingsNotPreservedDuringUpgrade(Exception):
    """Settings were not preserved during an upgrade"""

def upgrade_test(dut, build, mac):
    """Upgrade dut from current to build"""
    print 'HEADLINE: Enabling custom setting.'
    run(['xec', '-i', 'com.citrix.xenclient.xenmgr.config.ui',
         'set', 'wallpaper', CUSTOM_WALLPAPER], host=dut)
    run(['poweroff'], host=dut)
    print 'HEADLINE: upgrading to', build
    pxe_install_xc(dut, build=build, mac_address=mac, upgrade=True)
    wpsetting = run(['xec', '-i', 'com.citrix.xenclient.xenmgr.config.ui',
         'get', 'wallpaper', CUSTOM_WALLPAPER], host=dut, word_split=True)[0]
    if wpsetting != CUSTOM_WALLPAPER:
        raise SettingsNotPreservedDuringUpgrade(dut, 'latest', build,
                                                wpsetting, CUSTOM_WALLPAPER)

def entry_fn(dut, build, mac_address):
    upgrade_test(dut, build, mac_address)

def desc():
    return 'Upgrade XT from last release'
