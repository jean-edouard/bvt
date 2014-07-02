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

"""Describe builds; mainly used from ../results_server.py """
import os.path
from nevow.stan import xml
from serverlib.tags import space_span, script, a, em
from bvtlib.settings import CHANGE_REPORT_DIRECTORY

def describe_build(branch, build):
    """Return a nevow HTML description of a build"""
    change_report_dir = CHANGE_REPORT_DIRECTORY % (branch, build)
    if os.path.isdir(change_report_dir):
        content = os.listdir(change_report_dir)
        for stuff in content:
            if 'diff' in stuff or stuff.endswith('.error'):
                continue
            filename = os.path.join(change_report_dir, stuff)
            try:
                content = file(filename, 'r').read()
            except IOError:
                continue
            bod_start = content.find('<body>')
            bod_end = content.find('</body>')
            if bod_start  != -1 and bod_end != -1:
                return [xml(content[bod_start+6:bod_end])]
            else:
                return [space_span()['could not find body in ', filename]]
        return [space_span()[em['could not find build description in ', 
                             change_report_dir]]]
    else: 
        return [space_span()['could not find ', change_report_dir]]


def filters_to_path(filters):
    """Convert some filters to a URL path component, for use
    in cross references. """
    seg = ''
    for key in sorted(filters.keys()):
        for value in filters[key]:
            seg += '/%s=%s' % (key, value)
    return seg

def build_navigation(builds, build, filters={}):
    """Work out previous/next/latest links for a specific build,
    given other builds on the branch"""
    bnum = ( [(int(k.split('-')[2]), k) for k in builds
              if k.startswith('cam-oeprod-')])
    index = -1
    for index_prime, (_, build_prime) in enumerate(bnum):
        if build_prime == build: 
            index = index_prime
    if index == -1: 
        return []
    non_build_filters = dict([i for i in filters.items() if 
                              i[0] not in ['build', 'branch']])
    ref = filters_to_path(non_build_filters)
    out = []
    for label, offset, key in [('previous', lambda x: x-1, 'Left'),
                               ('next', lambda x: x+1, 'Right'),
                               ('latest', lambda x: -1, 'Ctrl+Right')]:
        try:
            _, altbuild = bnum[offset(index)]
        except IndexError:
            continue
        if altbuild == build: 
            continue
        text = [altbuild, ' (', label, ')', ' [', key, ']']
        target = '/build/'+altbuild
        out += [
            space_span()[a(href=target)[text]],
            script(type='text/javascript')[
                "shortcut.add(\"%s\", function(){ window.location=\"%s\"; });" %
                (key, target)]]
    return out
