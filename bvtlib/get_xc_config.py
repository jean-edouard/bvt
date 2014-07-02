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

"""Get contents of /etc/xenclient.conf"""

from bvtlib.exceptions import ExternalFailure
from bvtlib.wait_to_come_up import wait_to_come_up, InstallerRunning
from bvtlib.run import run
from re import compile

class UndefinedConfigField(ExternalFailure):
    """Undefined config field"""

def split_value_definition(line):
    k, _, v = line.partition(' = ')
    return (k, v)

def get_xc_config(dut, timeout=60):
    """Get config information for XC running on dut or throw exception"""
    print 'GET_XC_CONFIG: connect to', dut
    wait_to_come_up(dut, timeout=timeout, installer_okay=False)
    non_comment = compile('\\A[^#].+ = .+')
    lines = run(['cat','/etc/xenclient.conf'],
                timeout=timeout,
                host=dut,
                line_split=True)
    line_pairs = [ split_value_definition(line) 
                   for line in lines
                   if non_comment.match(line) ]
    return dict((key, value) for (key, value) in line_pairs)

def get_xc_config_field(dut, field, timeout=60, config=None, default_value=None):
    """Get a field of the configuration of DUT.
If the field is not defined, return default_value, which by default is None.
A cached config, from get_xc_config, may be given."""
    if config is None:
        config = get_xc_config(dut, timeout)
    if field in config:
        return config[field]
    else:
        return default_value

def try_get_xc_config_field(dut, field, timeout=60, config=None):
    """Get a field of the configuration of DUT.
If the field is not defined, raise an exception.
A cached config, from get_xc_config, may be given."""
    if config is None:
        config = get_xc_config(dut, timeout)
    if field in config:
        return config[field]
    else:
        raise UndefinedConfigField(dut, field)

