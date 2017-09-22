#
# Copyright (c) 2012 Citrix Systems, Inc.
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

"""Run callback and return success and result/exception"""
from traceback import print_exc
from src.bvtlib.exceptions import ExternalFailure

# TODO: use the with construct for this
def maybe(callback, description, verbose=True):
    """Run callback, returning (True, result) if it passes
    or (False, exception) if it fails """
    if verbose:
        print 'MAYBE: starting', description
    try: 
        return True, callback()
    except (Exception), exc:
        if verbose:
            print 'HEADLINE: failed to', description, 'exception', exc
        if not (isinstance(exc, SystemExit) or isinstance(exc, ExternalFailure)):
            print_exc()
        return False, exc

        
