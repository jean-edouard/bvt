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

from src.bvtlib.run import run
from src.bvtlib.exceptions import ExternalFailure

class AuthFailure(ExternalFailure): pass

def authentication_test(dut, target):
    host = target.split('.')[0]
    if run(['curl', '-s', '-S', '-k', '--ntlm', '-u', host + '\\\\admin:admin',
            'https://' + target + ':8443/rpc/ADAuth/'], host=dut) != (host.upper() + '\\admin'):
        raise AuthFailure()

def entry_fn():
    authentication_test(dut, sync_name)

def desc():
    return 'Test CURL NTLMv2 authentication to Synchronizer'
    
