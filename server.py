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

from async_events import channel
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

def server(worker_id):
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

    channel.init(proc_count)

    running = True

    # If a process dies for any reason, restart it unless it is time to quit
    def reloader(i):
        while running:
            print 'Starting worker {}.'.format(i)
            proc = gipc.start_process(server, (i,), daemon=True, name='worker{}'.format(i))
            proc.join()
            print 'Worker {} has just quit!'.format(i)
        print 'Done with worker {}'.format(i)

    # Spawn the reloaders for the workers
    reloaders = [gevent.spawn(reloader, i) for i in xrange(proc_count)]

    # Channel manager process reloader:
    while running:
        print 'Starting channel manager process.'
        proc = gipc.start_process(channel.rpc_dispatcher, daemon=True, name='channel_mngr')
        proc.join()
        print 'Channel manager process has quit.'
    print 'Done with channel manager'

    gevent.join_all(reloaders)
    print 'All done, quiting'

if __name__ == "__main__":
    main()
