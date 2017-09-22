#for operations about xen

from src.bvtlib.run import run


def total_mem(host):
    unparsed = run(['xenops', 'physinfo'],host=host,line_split=True)
    for line in unparsed:
        if "total_pages" in line:
            return int(line.split('(')[1].split(' ')[0])

def free_mem(host):
    unparsed = run(['xenops', 'physinfo'],host=host,line_split=True)
    for line in unparsed:
        if 'free_pages' in line:
            return int(line.split('(')[1].split(' ')[0])
