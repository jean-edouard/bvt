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

"""Run commands in guest using v4v"""
from bvtlib.run import run, space_escape
from bvtlib.domains import find_domain

def domid_to_dotted(domid):
    #domid is 16 bit
    return "1.0.%d.%d" % (domid>>8, domid & 0xff)

def run_v4v(dut, guest, args):
    status = find_domain(dut, guest)
    domaddr = domid_to_dotted(int(status['dom_id']))
    all_args = ['sshv4v', '-oStrictHostKeyChecking=no', '-oUserKnownHostsFile=/dev/null', domaddr] 
    all_args.extend(args)
    return run(space_escape(all_args), host=dut)
