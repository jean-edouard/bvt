

from src.bvtlib import mongodb


def determine_build(dut):
    mdb = mongodb.get_autotest()
    dut_doc = mdb.duts.find_one({'name':dut})
    return dut_doc['build']
    
