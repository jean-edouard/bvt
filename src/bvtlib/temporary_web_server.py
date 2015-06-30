from multiprocessing import Process, Queue
from socket import getfqdn, gethostbyname
from SocketServer import TCPServer
from os import chdir
from SimpleHTTPServer import SimpleHTTPRequestHandler

class UnableToDetermineServerAddress(Exception):
    """Unable to find an external address for this server. 

    If you are using Debian / Ubuntu see https://www.debian.org/doc/manuals/debian-reference/ch05.en.html#_the_hostname_resolution
    """

class TemporaryWebServer:
    """Run a temporary web server in this context manager, serving contents
    at path."""
    def __init__(self, path):
        """Run a web server temporarily for files in path."""
        self.path = path
        self.fqdn = getfqdn()
        print 'INFO: host name', self.fqdn
        assert not self.fqdn.startswith('127.0.0')
        self.port = None
        self.url = None
        self.process = None
        print 'INFO: constructed web server for', self.fqdn
    def __enter__(self):
        sockname_queue = Queue()
        self.process = Process(target=run, args=(self.fqdn, self.path,
                                                 sockname_queue))
        self.process.start()
        sockname = sockname_queue.get()
        self.port = sockname[1]
        self.url = 'http://%s:%d' % sockname
        print 'INFO: serving on', self.url
        return self
    def __exit__(self, _type, value, traceback):
        self.process.terminate()
        self.process.join()

def run(fqdn, path, sockname_queue):
    """Run web server on fqdn for path, push sockanme on sockname_queue.
    Never returns."""
    chdir(path)
    print 'INFO: starting web server on', fqdn
    httpd = TCPServer((gethostbyname(fqdn), 0), SimpleHTTPRequestHandler)
    print 'INFO: listening on', httpd.socket.getsockname()
    sockname = httpd.socket.getsockname()
    if sockname[0].startswith('127.0.'):
        raise UnableToDetermineServerAddress()
    sockname_queue.put(sockname)
    httpd.serve_forever()

