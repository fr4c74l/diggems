#!/usr/bin/env python
import os
import sys
import multiprocessing

import gevent
import gipc

from psycopg2 import extensions

from gevent.socket import wait_read, wait_write

from gevent_fastcgi.server import FastCGIServer
from gevent_fastcgi.wsgi import WSGIRequestHandler

from diggems import wsgi

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

peer_pipes = None

def server(worker_id, event_pipe):
    # The name of the Unix sockets:
    http_sockname = 'http{}.socket'.format(worker_id)
    ws_sockname = 'ws{}.socket'.format(worker_id)

    # Remove any old remaining socket entrypoint
    for sockname in (http_sockname, ws_sockname):
        try: os.unlink(sockname)
        except: pass

    # Serve wepsocket events application
    #TODO...

    # Serve the Django application
    server = FastCGIServer(http_sockname, WSGIRequestHandler(wsgi.application), max_conns=50000)

    print 'Worker {} serving...'.format(worker_id)
    server.serve_forever()

def main():
    # Make green psycopg:
    extensions.set_wait_callback(gevent_wait_callback)

    # Decide how many processes to use
    try:
        proc_count = int(sys.argv[1])
    except:
        proc_count = multiprocessing.cpu_count()

    # Create the pipes to publish on remote channels
    pipe_readers, peer_pipes = zip(*[gipc.pipe() for i in xrange(proc_count)])

    # If a worker dies for any reason, restart it unless it is time to quit
    running = True
    workers = [None] * proc_count
    def reloader(i):
        while running:
            print 'Starting worker {}.'.format(i)
            workers[i] = gipc.start_process(server, (i, pipe_readers[i]), daemon=True, name='worker{}'.format(i))
            workers[i].join()
            print 'Worker {} has just quit!'.format(i)
        print 'Done with worker {}'.format(i)

    # Spawn the reloaders for the workers
    reloaders = [gevent.spawn(reloader, i) for i in xrange(1, proc_count)]
    reloader(0) # No need to spawn an extra greenlet for the first worker

    gevent.join_all(reloaders)
    print 'All done, quiting'

if __name__ == "__main__":
    main()
