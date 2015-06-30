#!/usr/bin/python

from src.bvtlib.mongodb import get_autotest
from src.bvtlib.settings import TEST_NODES
from src.testcases.test_cases import TEST_CASES
from pymongo.collection import Collection

def setup_collections(mdb):
    Collection(mdb,'duts',create=True)
    Collection(mdb,'test_cases',create=True)
    Collection(mdb,'builds',create=True)
    Collection(mdb,'jobs',create=True)
    Collection(mdb,'results',create=True)


def add_default_test_nodes(mdb):
    for i in range(TEST_NODES):
        mdb.duts.save({'name':"10.20.1.%s"%str(10+i), '_id':"10.20.1.%s"%str(10+i),
             'power_control':'AMT', 'result_id':'0','mac':'changeme'})

def add_default_test_cases(mdb):
    for i,tc in enumerate(TEST_CASES):
        mdb.test_cases.save({'_id':i, 'name':tc['function'].__name__, 
                                'description':tc['description']})
def main():
    mdb = get_autotest()
    setup_collections(mdb)
    add_default_test_nodes(mdb)
    add_default_test_cases(mdb)

main()
