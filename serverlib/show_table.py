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

"""Produce paginated tables"""
from serverlib.tags import space_span, table, a, tr, td, th
from src.bvtlib import mongodb
import time


def show_table(headings, rows, offset, show_rows, cross_reference, complete=False,
               show_nav=True):
    """Show a paginated table"""
    top = space_span()[a(href='/')['up']]
    backwards = [('-' + str(show_rows), 
                 max(0, offset - show_rows))] if offset > 0 else []
    forwards = [] if complete else [
        ('+'+str(show_rows), max(0, offset+show_rows))] 
    start = [] if offset <= show_rows else [('0', 0)]
    navs = [top, [space_span()[a(href=cross_reference(noffset, show_rows))[label]]
        for label, noffset in forwards + backwards + start]] if (show_rows and show_nav) else []
    return [navs, table[headings, rows], navs]

def add_td(x):
    if repr(x).startswith("Tag('td'"): 
        return x
    else: 
        return td[x]

def add_ts(x):
    if repr(x).startswith("Tag('td'"): 
        return x
    else: 
        return td(**{'class':'step_cell'})[x]

def normalise(x):
    if type(x) == type(''):
        return (x, lambda row: row.get(x, '-'))
    else:
        return x

def produce_table(cursor, columns, cross_reference, offset=0, show_rows=20,
                  row_fn=lambda doc, body: tr[body], 
                  show_nav=True):
    col2 = [ normalise(c) for c in columns]
    headings = tr[[ th[l] for l, _ in col2]]
    rows = []
    for doc in cursor:
        rows.append( row_fn(doc, [add_td(fn(doc)) for 
                     _,fn in col2]))
    return show_table(headings, rows, offset, show_rows, cross_reference, show_nav=show_nav)

# Modification of produce table that generates extra rows for each step of
# the test suite.  Links from the main /results page.
def suite_table(cursor, columns, cross_reference, offset=0, show_rows=20,
                row_fn=lambda doc, body: tr[body],
                show_nav=True):
    col2 = [ normalise(c) for c in columns]
    headings = tr[[ th[l] for l, _ in col2]]
    rows = []
    mdb = mongodb.get_autotest()
    for doc in cursor:
        rows.append(row_fn(doc, [add_td(fn(doc)) for _,fn in col2]))
        for i in range(doc['steps']):
            rows.append(row_fn(doc, [add_ts('step'+str(i)), add_td(doc['step'+str(i)]),
                                add_td(''.join(mdb.suites.find_one({'name':doc['suite']})['s-%s'%str(i)])),
                                add_td(time.asctime(time.localtime(doc['step%s-start'%str(i)]))),
                                add_td(time.asctime(time.localtime(doc['step%s-end'%str(i)]))),
                                add_td(doc['step%s-reason'%str(i)])], str(i)))
    return show_table(headings, rows, offset, show_rows, cross_reference, show_nav=show_nav)
        
def simple_table(cursor, columns):
    return produce_table(cursor, columns, show_nav=False, cross_reference=None, show_rows=1e9)
