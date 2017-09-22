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

from serverlib import tags
from nevow import flat
from multiprocessing import Process, Queue
import sys, socket, cStringIO, time
from  BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler

class Page:
    def __init__(self, port, get_page_function_generator, 
                 tick_function_generator=None):
        self.get_page_function_generator = get_page_function_generator
        self.tick_function_generator = tick_function_generator
        self.port = port
        self.url = 'http://'+socket.getfqdn()+':'+str(port)
        self.start_time = time.time()
    isLeaf = True
    
    def do_get_page(self, request):
        try:
            get_page = self.get_page_function_generator()
            content = get_page(self,request)
            request.write(content)
        except Exception,e:
            f = failure.Failure()
            out = cStringIO.StringIO()
            f.printTraceback(out)
            print out.getvalue()
            request.write( str(flat.flatten(tags.html[
                            tags.h1['Internal failure'],
                            tags.pre[out.getvalue()]])))
        request.finish()
    def render_GET(self, request, retry_db=True): 
        self.do_get_page(request)
        return NOT_DONE_YET
    def render_POST(self, request): return self.render_GET(request)
    
    def do_tick(self):
        if self.tick_function_generator is None: return
        try:
            tick = self.tick_function_generator()
            tick(self)
        except:
            f = failure.Failure()
            f.printTraceback()
        else: print 'no tick'
        reactor.callLater(600.0, self.do_tick) # pylint: disable=E1101

def launch(queue, port, get_page_function_generator, args=[]):
    """Start server"""
    class MyHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            text = get_page_function_generator(self, *args)
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.send_header('Content-length', len(text))
            self.end_headers()
            self.wfile.write(text)
    httpd = HTTPServer(('', port), MyHandler)
    sa = httpd.socket.getsockname()
    queue.put(sa)
    print 'Serving on', sa
    httpd.serve_forever()
    
def start(port, get_page_function_generator, *args):
    """Start the server in another process"""
    queue = Queue()
    process = Process(target = launch, args= 
                      (queue, port, get_page_function_generator, args))
    process.start()
    sa = queue.get()
    print 'understood serving on', sa
    return sa[1], process
    
def module_function_generator(module_name, function_name):
    def generator():
        module =__import__(module_name)
        reload(module)
        if not hasattr(module, function_name): return
        return getattr(module, function_name)
    return generator

def main(module_name):
    if len(sys.argv) < 2:
        print 'USAGE: %s PORT_NUMBER' % (sys.argv[0])
        sys.exit(1)
    try: port = int(sys.argv[1])
    except ValueError: 
        print 'bad port number %r' % (sys.argv[1])
        sys.exit(2)
    start(port, 
          module_function_generator(module_name, 'get_page'),
          module_function_generator(module_name, 'tick'))
    reactor.run() # pylint: disable=E1101

