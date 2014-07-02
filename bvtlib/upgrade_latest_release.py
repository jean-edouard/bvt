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

from bvtlib.pxe_install_xc import pxe_install_xc
from bvtlib.settings import CUSTOM_WALLPAPER
from bvtlib.ensure import ensure
from bvtlib.domains import find_domain
from bvtlib.run import run

class SettingsNotPreservedDuringUpgrade(Exception):
    """Settings were not preserved during an upgrade"""

def upgrade_last_release(dut, build):
    """Upgrade dut from latest release to build"""
    print 'HEADLINE: installing latest release build from scratch'
    pxe_install_xc(dut, release='latest', upgrade=False)
    ensure(dut, 'win7')
    run(['xec', '-i', 'com.citrix.xenclient.xenmgr.config.ui',
         'set', 'wallpaper', CUSTOM_WALLPAPER], host=dut)
    run(['poweroff'], host=dut)
    print 'HEADLINE: upgrading to', build
    pxe_install_xc(dut, build=build, upgrade=True)
    wpsetting = run(['xec', '-i', 'com.citrix.xenclient.xenmgr.config.ui',
         'get', 'wallpaper', CUSTOM_WALLPAPER], host=dut, word_split=True)[0]
    if wpsetting != CUSTOM_WALLPAPER:
        raise SettingsNotPreservedDuringUpgrade(dut, 'latest', build,
                                                wpsetting, CUSTOM_WALLPAPER)
    find_domain(dut, 'win7')

TEST_CASES = [{
        'description': 'Upgrade XT from last release',
        'trigger': 'platform install',
        'function': upgrade_last_release, 'bvt':True,
        'command_line_options': ['--upgrade-latest-release'],
        'arguments' : [('dut','$(DUT)'), ('build', '$(BUILD)')]}]
