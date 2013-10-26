#!/usr/bin/env python

# Just in case I forgot something, but we should use
# gevent explicity wherever we can
from gevent import monkey; monkey.patch_all()

import os
import sys
import shutil
import multiprocessing
import traceback
import signal
import setproctitle

import gevent
import gipc

from psycopg2 import extensions

from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
from gevent import socket

from gevent_fastcgi.server import FastCGIServer
from gevent_fastcgi.wsgi import WSGIRequestHandler

from diggems import wsgi
from async_events import channel, ws_dispatcher

# Patch to make psycopg2 green
def gevent_wait_callback(conn, timeout=None):
    """A wait callback useful to allow gevent to work with Psycopg."""

    while True:
        state = conn.poll()
        if state == extensions.POLL_OK:
            break
        elif state == extensions.POLL_READ:
            #print 'Greenlet waiting on READ'
            socket.wait_read(conn.fileno(), timeout=timeout)
        elif state == extensions.POLL_WRITE:
            #print 'Greenlet waiting on WRITE'
            socket.wait_write(conn.fileno(), timeout=timeout)
        else:
            raise psycopg2.OperationalError(
                "Bad result from poll: %r" % state)

def watcher(func):
    try:
        while 1:
            func()
    except:
        traceback.print_exc()
        # Must quit the process so the watcher process can restart
        print 'Quiting the faulty process...'
        sys.exit(1)

sock_dir = 'sockets'

def server(worker_id):
    setproctitle.setproctitle('diggems worker {}'.format(worker_id))

    # The name of the Unix sockets:
    http_sockname = '{}/http{}.socket'.format(sock_dir, worker_id)
    ws_sockname = '{}/ws{}.socket'.format(sock_dir, worker_id)

    channel.worker_init(worker_id)

    # Serve websocket events application
    ws_sock_listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    ws_sock_listener.bind(ws_sockname)
    ws_sock_listener.listen(128)
    ws_server = pywsgi.WSGIServer(ws_sock_listener, ws_dispatcher.dispatcher, handler_class=WebSocketHandler)

    # Serve the Django application
    http_server = FastCGIServer(http_sockname, WSGIRequestHandler(wsgi.application), max_conns=5000)

    print 'Worker {} serving...'.format(worker_id)
    gevent.spawn(watcher, ws_server.serve_forever)
    watcher(http_server.serve_forever)

running = True

workers = None
channel_mngr = None

# If a process dies for any reason, restart it unless it is time to quit
def reloader(i):
    global running, workers
    while running:
        print 'Starting worker {}.'.format(i)
        workers[i] = gipc.start_process(server, (i,), daemon=True, name='worker{}'.format(i))
        workers[i].join()
        print 'Worker {} has just quit!'.format(i)
    print 'Done with worker {}'.format(i)

def sig_quit():
    global running, workers, channel_mngr
    running = False
    for w in workers:
        os.kill(w.pid, signal.SIGINT)
    
    if channel_mngr:
        os.kill(channel_mngr.pid, signal.SIGINT)

def main():
    global running, channel_mngr, workers

    # Make green psycopg:
    extensions.set_wait_callback(gevent_wait_callback)

    # Decide how many processes to use
    try:
        proc_count = int(sys.argv[1])
    except:
        proc_count = multiprocessing.cpu_count()

    workers = [None] * proc_count

    channel.init(proc_count)
    
    gevent.signal(signal.SIGINT, sig_quit)
    gevent.signal(signal.SIGTERM, sig_quit)
    
    # Remove the sockets directory
    shutil.rmtree(sock_dir, True)
    os.mkdir(sock_dir)

    # Spawn the reloaders for the workers
    reloaders = [gevent.spawn(reloader, i) for i in xrange(proc_count)]

    setproctitle.setproctitle('diggems master')

    # Channel manager process reloader:
    while running:
        print 'Starting channel manager process.'
        proc = gipc.start_process(channel.rpc_dispatcher, daemon=True, name='channel_mngr')
        proc.join()
        print 'Channel manager process has quit.'
    print 'Done with channel manager'

    gevent.joinall(reloaders)
    print 'All done, quiting'

if __name__ == "__main__":
    main()
