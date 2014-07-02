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

from bvtlib.run import run, SubprocessError
from bvtlib.exceptions import ExternalFailure

class AdminUIFailure(ExternalFailure): pass

def admin_ui_check(target):
    # check we get redirected
    if run(['curl', '-o', '/dev/null', '-s', '-S', '-k', '-w', '%{http_code} %{redirect_url}', 'https://' + target + '/']) != ("301 https://" + target + ":8443/"):
        raise AdminUIFailure()
    # check a sample admin rpc doesn't exist
    if run(['curl', '-o', '/dev/null', '-s', '-S', '-k', '-w', '%{http_code}', 'https://' + target + '/rpc/Users/list']) != '404':
        raise AdminUIFailure()
    # check we get SSL handshake error (i.e. server asks for client cert)
    try:
        run(['curl', '-o', '/dev/null', '-s', '-S', '-k', 'https://' + target + '/rpc/JSON/Device.Bind'])
    except SubprocessError as e:
        if e.args[1] != 52 and e.args[1] != 56:
            raise AdminUIFailure()
    else:
        raise AdminUIFailure()

TEST_CASES = [{
    'description': "Check the admin UI isn't available on port 443 of Synchronizer",
    'function': admin_ui_check,
    'trigger': 'first',
    'command_line_options': ['--admin-ui-check'],
    'arguments': [('target', '$(SYNCHRONIZER_NAME)')]
    }]

