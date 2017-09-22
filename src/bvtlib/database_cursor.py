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

import psycopg2, psycopg2.extras

def make_query(rows_and_tables, positional, conditions):
    condl = sorted(conditions.keys())
    if not condl: return rows_and_tables, tuple(positional)
    if 'WHERE' in rows_and_tables: sep = ' AND '
    else: sep = ' WHERE '
    condl2 = tuple( list(positional) + [conditions[k] for k in condl])
    return rows_and_tables+sep + ' AND '.join( 
        '%s=%%s' % k for k in condl), condl2 


class NoRows(Exception): pass
class MultipleRows(Exception): pass


class DatabaseCursor:
    def __init__(self, dbname, host, user, pwd, isolation_level='unspecified'):
        db_connection= psycopg2.connect(
            "dbname=%s host=%s user=%s password=%s" % (dbname, host, user, pwd),
            connection_factory=psycopg2.extras.DictConnection)
        if isolation_level != 'unspecified': 
            db_connection.set_isolation_level(isolation_level)
        self.db_connection = db_connection
        self.dbcursor = db_connection.cursor()
        self.fetchall = self.dbcursor.fetchall
        self.verbose = False
    
    def execute(self, *l, **d):
        r = self.dbcursor.execute(*l, **d)
        self.db_connection.commit()
        return r
    
    def select(self, rows_and_tables, *positional, **d):
        rows_and_tables2,positional2=make_query(rows_and_tables,positional,d)
        sql = 'SELECT '+rows_and_tables2
        if self.verbose: print 'SQL-QUERY:',sql,positional2
        self.dbcursor.execute(sql,positional2)
        r = self.fetchall()
        self.db_connection.commit()
        return r
    
    def select1_field(self, column, rows_and_tables, *l,**d):
        return self.select1(column + ' FROM '+rows_and_tables, *l, **d)[column]
    
    def select1(self, rows_and_tables, *positional, **d):
        not_found_exception = d.pop('not_found_exception', NoRows)
        multiple_rows_exception = d.pop('multiple_rows_exception',MultipleRows)
        rows_and_tables2,positional2=make_query(rows_and_tables, positional, d)
        sql = 'SELECT '+rows_and_tables2
        if self.verbose: 
            print 'SQL-QUERY:',sql,'values',repr(tuple(positional2))
        self.dbcursor.execute(sql, positional2)
        res = self.dbcursor.fetchall()
        self.db_connection.commit()
        if self.verbose: print 'SQL-ROWS: query result',res
        if res == []: raise not_found_exception(rows_and_tables2,positional2)
        if len(res) > 1: 
            raise multiple_rows_exception(len(res),rows_and_tables2,positional2)
        return res[0]
    
    def insert1(self, table, **columns):
        klist = sorted(columns.keys())
        vlist = [columns[key] for key in klist]
        sql = 'INSERT INTO %s (%s) VALUES (%s)' % (
            table, ','.join(klist), ','.join(['%s']*len(klist)))
        self.execute(sql, tuple(vlist))
        self.db_connection.commit()
    
    def get_id(self, id_field, table, **columns):
        if self.select('* FROM '+table, **columns) == []:
            self.insert1(table, **columns)
            self.db_connection.commit()
        return self.select1_field(id_field,table,**columns)
    
    def commit(self): self.db_connection.commit()


class NoCredentials(Exception): 
    """No credentials in src.bvtlib.settings.DATABASE_CREDENTIALS for requested database"""
    
def open_database(name):
    """Open connection database name"""
    credentials = None
    if credentials is None:
        raise NoCredentials(name)
    credentials = dict(credentials)
    credentials.setdefault('user', name)
    credentials.setdefault('dbname', name)
    return DatabaseCursor( **credentials)

open_state_db = lambda: open_database('statedb')
open_asset_db = lambda: open_database('assetdb')
open_config_db = lambda: open_database('configdb')

schema = """
-- to create results database:
CREATE USER "resultsdb" WITH PASSWORD 'granEund5';
CREATE DATABASE "resultsdb";
"""
resultsdb_schema = """
GRANT ALL PRIVILEGES ON DATABASE resultsdb TO resultsdb;

CREATE TABLE builds (
  build_index SERIAL PRIMARY KEY,
  build TEXT NOT NULL UNIQUE,
  avoid TEXT,
  branch TEXT NOT NULL DEFAULT 'master',
  release TEXT
);
GRANT ALL PRIVILEGES ON builds, builds_build_index_seq TO resultsdb;

CREATE TABLE test_cases (
  test_case_index SERIAL PRIMARY KEY,
  test_case TEXT NOT NULL UNIQUE, 
  description TEXT,
  hide INTEGER
);
GRANT ALL PRIVILEGES ON test_cases, test_cases_test_case_index_seq TO resultsdb;

CREATE TABLE duts (
  dut_index SERIAL PRIMARY KEY,
  dut TEXT NOT NULL UNIQUE,
  automate INTEGER NOT NULL DEFAULT 0,
  source_tree TEXT NOT NULL DEFAULT '/usr/local/src/bvt',
  last_launch_time TIMESTAMP WITH TIME ZONE,
  memory INTEGER, -- in megabytes
  control_pid INTEGER,
  model TEXT, 
  power_control TEXT NOT NULL DEFAULT 'AMT', -- parameters for power control
  location TEXT, -- human description of laptop location
  current_result_index INTEGER, 
  branch TEXT NOT NULL DEFAULT 'master',
  problem_wait TIMESTAMP WITH TIME ZONE, -- when current failure wait will end
  experiment TEXT, -- run this experiments command instead of BVT
  experiment_install INTEGER NOT NULL DEFAULT 0 -- automatically rebuild on next experiment
);
GRANT ALL PRIVILEGES ON duts, duts_dut_index_seq TO resultsdb;

CREATE TABLE results (
  result_index SERIAL PRIMARY KEY,
  build_index INTEGER REFERENCES builds(build_index) ON DELETE CASCADE,
  test_case_index INTEGER NOT NULL REFERENCES test_cases(test_case_index
                                                          ) ON DELETE CASCADE,
  dut_index INTEGER REFERENCES duts(dut_index) ON DELETE CASCADE,
  failure TEXT, -- reason for failure or empty string on success
  database_log TEXT NOT NULL, -- sqlite database containg test log
  start_time TIMESTAMP WITH TIME ZONE,
  end_time TIMESTAMP WITH TIME ZONE,
  modification_time TIMESTAMP WITH TIME ZONE, -- last time this row changed
  git_id TEXT,
  whiteboard TEXT,
  status TEXT -- most recent headline
);
GRANT ALL PRIVILEGES ON results, results_result_index_seq TO resultsdb;

"""

if 0:
    schema += """
CREATE INDEX results_by_dut_build ON results ( dut_index, build_index);
CREATE INDEX results_by_test_case_build ON results ( test_case_index, build_index);
"""
