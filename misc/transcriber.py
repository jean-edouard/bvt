#! /scratch/autotest_python/bin/python
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

"""One shot import of postgresql data to mongodb"""

from bvtlib import database_cursor, mongodb, process_result, mongodb
import socket, time, datetime

def dt_to_epoch(dtval): 
    """convert datetime to epoch seconds"""
    return time.mktime(dtval.timetuple()) if dtval else None

def main():
    """go go go"""
    rdb = database_cursor.open_results_db()
    mongo = mongodb.get_autotest()
    hostname = socket.gethostname()
    # note: we are deliberately ignoring results with foreign keys that 
    # do not match in builds / test_cases / duts
    offset = 0
    mdb = mongodb.get_autotest()
    while 1:
        rows = rdb.select('* FROM results NATURAL JOIN duts '+
                          'NATURAL JOIN builds NATURAL JOIN test_cases WHERE '
                          'start_time > %s ORDER BY start_time DESC OFFSET '+
                          str(offset)+' LIMIT 10',
                          (datetime.datetime.today() - datetime.timedelta(14)))
        for row in rows:
            query = {'automation_server' : hostname,
                     'result_index' : row['result_index'] }
            doc = mdb.results.find_one(query)
            new = doc is None
            if new: 
                doc = query
            for key, value in [
                ('start_time', dt_to_epoch(row['start_time'])),
                ('end_time', dt_to_epoch(row['end_time'])),
                ('test_case', row['test_case']),
                ('automation_server', hostname),
                ('failure', row['failure']),
                ('build', row['build']),
                ('branch', row['branch']),
                ('dut', row['dut'])]:
                if value is not None:
                    doc[key] = value 
            offset += 1
            _id = mdb.results.save(doc)
            doc['_id'] = _id
            print row['result_index'], '->', _id, 'NEW' if new else 'OLD', 
            print row['start_time']
            if new:
                process_result.process_result(doc, mongo=mongo)
            else:
                break
        if len(rows) < 10 or not new:
            break
if __name__ == '__main__': 
    main()
    
