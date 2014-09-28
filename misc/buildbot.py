#!/usr/bin/python

from src.bvtlib.settings import BUILDBOT2_ALL_BUILDERS_URL,BUILDBOT2_BUILDER_URL,BUILDBOT2_BUILDER_FORMAT
from json import loads
from urllib import urlopen
from src.bvtlib import mongodb
from src.bvtlib.set_build_information import set_build_information
import time

MDB = mongodb.get_autotest()

def get_build_doc(build, branch):
    """get a mongo build document for build on branch"""
    #branch = '-'.join(build.split('-')[3:])
    doc = {'_id':build, 'branch':branch}
    build_doc = MDB.builds.find_one(doc)
    if build_doc is None:
        MDB.builds.save(dict(doc, timestamp=time.time()))
        build_doc = MDB.builds.find_one(doc) # to get ID
    assert build_doc, doc
    return build_doc

def construct_build_record(doc, build_url_pattern, builder):
    subdoc = {}
    subdoc['buildbot_number'] =doc['number']
    subdoc['buildbot_url']= build_url_pattern  % (builder, doc['number'])
    subdoc['build_output'] = doc['build_output']
    
    if doc['eta']:
        subdoc['eta_time'] =  time.time() + doc['eta']
    if len(doc.get('times', [])) == 2 and doc['times'][1]:
        subdoc['build_time'] = doc['times'][1]
    if doc.get('text') == ['exception', 'interrupted']:
        subdoc['failure'] = 'interrupted'
    if type(doc.get('steps')) == type([]):
        prev = None
        seenedge = False
        for step in doc['steps']:
            if step['text'][-1:] == ['failed'] and \
                    subdoc.get('failed') is None:
                subdoc['failure'] = ' '.join(step['text'])
                subdoc['failure_log_url'] = subdoc['buildbot_url']+ '/steps/' + step['name'] + '/      logs/stdio'
            if not seenedge:
                if prev is None:
                    prevdone = True
                else:
                    prevdone = prev.get('isFinished') and \
                        prev['results'][0] == 0
                if step.get('isStarted') and prevdone:
                    if step['isFinished'] == False:
                        logurl = subdoc['buildbot_url']+'/steps/'+step['name']+'/logs/stdio/text'
                        text = ''
                        if 0:
                            print 'downloading', logurl
                            log = urlopen(logurl).read()
                            print 'read', len(log), 'from', logurl
                            for line in log.splitlines():
                                if line.startswith('NOTE:'):
                                    text = line[5:]
                                if line and text == '':
                                    text = line
                        stats = step['statistics']
                        if 'bb_current_task' in stats and \
                                'bb_task_number' in stats:
                            ex = ' step %d of %d' % (
                                stats['bb_current_task'],
                                stats['bb_task_number'])
                        else:
                            ex = ''
                        subdoc['status'] = 'build step '+ \
                            step['name']+' running '+text+ex
                        seenedge = True
                    elif 'results' in step and step['results'][0] == 2:
                        subdoc['failure'] = ' '.join(step['text'])
                        subdoc['status'] = 'build step '+ \
                           step['name']+ ' failed'
                        seenedge = True
            prev = step
    return subdoc



def inspect_buildbot():
    if BUILDBOT2_ALL_BUILDERS_URL is None:
        return
    tdoc = loads(urlopen(BUILDBOT2_ALL_BUILDERS_URL).read())
    for builder in tdoc:
        doc = tdoc[builder]
        latest = max(doc['cachedBuilds']+doc['currentBuilds'])
        for offset in range(10):
            bnum = latest - offset
            if bnum < 0:
                break
            try:
                doc = loads(urlopen((BUILDBOT2_BUILDER_URL % (builder))+'/builds/'+str(bnum)).         read())
            except ValueError:
                print 'WARNING: unable to decode', builder, bnum
                continue
            #pprint.pprint(doc)
            if 'properties' not in doc:
                continue
            propdict = dict( [ (x[0], x[1]) for x in doc['properties']])
            tag = propdict.get('tag' if builder == 'XT_Tag' else 'revision')
            if tag is None:
                print 'WARNING: No tag for', builder, bnum
                continue
            #if not tag.startswith('cam-oeprod-'):
            #    print 'WARNING: ignoring unexpected tag', tag
            #    continue
            #if tag == "":
            #    build_doc = get_build_doc(str(bnum), propdict['branch'])
            #else:
            #    build_doc = get_build_doc(tag, propdict['branch'])
            build_doc = get_build_doc(str(bnum)+'-'+doc['builderName'], propdict['branch'])
            subdoc = construct_build_record(doc, BUILDBOT2_BUILDER_FORMAT, builder)
            set_build_information(str(bnum)+'-'+doc['builderName'], {builder:subdoc})
            #set_build_information(tag, {builder:subdoc})
            # the deployed watcher.git expects the build record to be called platform
            # so duplicate installer builds there for now. TODO: remove this once 
            # watcher.git has been updated.
            if builder == 'XT_installer':
                set_build_information(tag,{'platform':subdoc})


def main():
    inspect_buildbot()

main()
