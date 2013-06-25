#!/usr/bin/env python
import os
from psycopg2 import extensions

from gevent.socket import wait_read, wait_write

from gevent_fastcgi.server import FastCGIServer
from gevent_fastcgi.wsgi import WSGIRequestHandler

from diggems.wsgi import application

# Patch to make psycopg2 green
def gevent_wait_callback(conn, timeout=None):
    """A wait callback useful to allow gevent to work with Psycopg."""

    while True:
        state = conn.poll()
        if state == extensions.POLL_OK:
            break
        elif state == extensions.POLL_READ:
            #print 'Greenlet waiting on READ'
            wait_read(conn.fileno(), timeout=timeout)
        elif state == extensions.POLL_WRITE:
            #print 'Greenlet waiting on WRITE'
            wait_write(conn.fileno(), timeout=timeout)
        else:
            raise psycopg2.OperationalError(
                "Bad result from poll: %r" % state)

def main():
    # Make green psycopg:
    extensions.set_wait_callback(gevent_wait_callback)

    # Remove any old remaining socket entrypoint
    try:
        os.unlink('fcgi-socket')
    except:
        pass

    # Serve the Django application
    request_handler = WSGIRequestHandler(application)
    server = FastCGIServer('fcgi-socket', request_handler, max_conns=50000, num_workers=4)
    print "Serving..."
    server.serve_forever()

if __name__ == "__main__":
    main()
