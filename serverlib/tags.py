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

#pylint: disable-msg=E0611,E1103,W0611,C0103

from nevow.tags import html, body, table, td, tr, a, h1, h2, h3, pre
from nevow.tags import xml, p, span, th, div, script, head, em, strong
from nevow.tags import form, select, option, ol, li, style, head, title
from nevow.tags import input as stan_input
import nevow.flat

def space_span(): 
    return span(style='margin: 1em')

def html_page(*nodes):
    """render a page of nodes as text"""
    return str(nevow.flat.flatten(html[nodes]))

def html_fragment(*nodes):
    """render nodes directly as a HTML fragment

    specifically there is. no <HTML> top level node """
    return str(nevow.flat.flatten(nodes))
