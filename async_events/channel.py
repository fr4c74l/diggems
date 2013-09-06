# Copyright 2013 Fractal Jogos e Tecnologia
# Software under Affero GPL license, see LICENSE.txt

import gevent
import gipc
import weakref
import inspect
import sys
import os
import cPickle as pickle
import fd_trick
import struct

from gevent import socket
from decorator import FunctionMaker
from geventwebsocket.websocket import WebSocket, WebSocketError
from geventwebsocket.logging import create_logger

class _Subscriber(object):
    __slots__ = ('ws', 'deliverer')
    def __init__(self, ws):
        self.ws = ws
        self.deliverer = None

class Channel(object):
    __slots__ = ('name', 'ch_type', 'next_seqnum', 'first_seqnum', 'msg_history', 'subscribers')
    def __init__(self, channel_name, channel_type):
        self.name = channel_name
        self.ch_type = channel_type
        self.next_seqnum = 1
        self.first_seqnum = 1
        self.msg_history = {}
        self.subscribers = {}

    def subscribe(self, ws, from_seqnum=None):
        sb = _Subscriber(ws)
        self.subscribers[ws.unique_id] = sb
        if from_seqnum is not None and self.next_seqnum > from_seqnum:
            sb.deliverer = gevent.spawn(self._deliver, sb, from_seqnum)

    def unsubscribe(self, sb):
        if sb.deliverer:
            sb.deliverer.kill(block=True)
        del self.subscribers[sb.ws.unique_id]
        self._try_self_destroy()

    def post_message(self, msg):
        seqnum = self.next_seqnum
        self.next_seqnum += 1

        msg = '\n'.join((self.ch_type, str(seqnum), msg))
        self.msg_history[seqnum] = msg

        # Ideally, this send procedure should attempt to
        # send the messages in non-blocking way, and only if
        # it fails, spawn a sender greenlet, but WebSocket API
        # doesn't expose such functionality (try_send() or such).
        # TODO: implement try_send
        undelivering = [sb for sb in self.subscribers.itervalues() if not sb.deliverer]
        spawn_count = 0
        for sb in undelivering:
            sb.deliverer = gevent.spawn(self._deliver, sb, seqnum)
            # Yield at each 100 greenlets so that they may complete
            # and release memory...
            spawn_count += 1
            if spawn_count >= 100:
                spawn_count = 0
                gevent.sleep(0)

        # Messages will be held in channel for 5 minutes.
        gevent.spawn_later(300, self._trash_old, seqnum)

    def _trash_old(self, seqnum):
        i = self.first_seqnum
        while i <= seqnum:
            del self.msg_history[i]
            i += 1
        self.first_seqnum = i
        self._try_self_destroy()

    def _try_self_destroy(self):
        if not self.subscribers and not self.msg_history:
            del _channels[(self.name, self.ch_type)]

    def _deliver(self, sb, seqnum):
        ws = sb.ws

        try:
            if seqnum < self.first_seqnum:
                seqnum = self.first_seqnum
            while seqnum < self.next_seqnum:
                msg = self.msg_history[seqnum]
                ws.send(msg, False)
                seqnum += 1
        except socket.error, WebSocketError:
            # We want no part on websockts that can't deliver
            sb.deliverer = None
            self.unsubscribe(sb)
            return

        sb.deliverer = None

    def force_stop(self):
        for sb in self.subscribers:
            if sb.deliverer:
                sb.deliverer.kill(block=False)

_ws_refs = weakref.WeakValueDictionary()

# To generate new ids for websocket on worker (warps after trillons of years):
_ws_id_iterator = None

_worker_count = 1

_rpc_map = {}
_rpc_next_id = 0

(_call_endpoint, _handle_endpoint) = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)

def _ws_serialize(websocket):
    try:
        uid = websocket.environ['unique_id']
    except KeyError:
        uid = _ws_id_iterator.next()
        websocket.environ['unique_id'] = uid

    return (websocket.handler.socket.fileno(), uid)

def _ws_from_fd(fd):
    class PassiveWebSocket(WebSocket):
        __slots__ = ('__weakref__', 'unique_id')
        def __init__(self, *args, **kwargs):
            WebSocket.__init__(self, *args, **kwargs)

        def __del__(self):
            # Deleting the object must not close it, since it may
            # still br in use by the other process...
            pass

    class RecvStream(object):
        __slots__ = ('sock', 'write')
        def __init__(self, handler):
            self.sock = socket.fromfd(handler, socket.AF_INET, socket.SOCK_STREAM)
            self.write = self.sock.sendall

        def read(self, size):
            raise NotImplementedError("I didn't expect reads to occur from this copy of the socket...")

    class PseudoHandler(object):
        __slots__ = ('logger')
        def __init__(self, fd):
            self.logger = create_logger('ws_'.format(fd), True)

    return PassiveWebSocket(None, RecvStream(fd), PseudoHandler(fd))

def _ws_deserialize(ws_fd, ws_uid):
    try:
        ws = _ws_refs[ws_uid]
        os.close(ws_fd)
    except KeyError:
        ws = _ws_from_fd(ws_fd)
        ws.unique_id = ws_uid
        _ws_refs[ws_uid] = ws
    return ws

def _rpc(func):
    global _rpc_next_id, _rpc_map

    # Store function in the call map
    func_id = _rpc_next_id
    _rpc_next_id += 1
    _rpc_map[func_id] = func
    
    # For local usage of the function, append a _ in the name
    #globals()['_' + func.__name__] = func

    # Handle special parameter 'websocket'
    func_meta = inspect.getargspec(func)
    try:
        ws_idx = func_meta.args.index('ws')
    except ValueError:
        ws_idx = -1

    defaults = func_meta.defaults

    def ws_proxy_call(*args, **kwar):
        if len(args) > ws_idx:
            (ws_fd, ws_uid) = _ws_serialize(args[ws_idx])
            args = list(args)
            args[ws_idx] = ws_uid
            ws_locator = ws_idx
        else:
            try:
                ws = kwar['ws']
            except KeyError:
                ws = defaults[ws_idx]
            (ws_fd, ws_uid) = _ws_serialize(ws)
            kwar['ws'] = ws_uid
            ws_locator = None
        msg = pickle.dumps((func_id, args, kwar, ws_locator), pickle.HIGHEST_PROTOCOL)
        ret = fd_trick.send_with_fd(_call_endpoint, msg, ws_fd)
        if ret != len(msg):
            # TODO: Weird! Can this ever happen? Maybe if message is too big.
            # Do something about it...
            pass

    def proxy_call(*args, **kwar):
        msg = pickle.dumps((func_id, args, kwar), pickle.HIGHEST_PROTOCOL)
        ret = _call_endpoint.send(msg)
        if ret != len(msg):
            # TODO: Weird! Can this ever happen? Maybe if message is too big.
            # Do something about it...
            pass

    # Have no ideia of how this works, just copied from decorator.py:
    evaldict = func.func_globals.copy()
    evaldict['_call_'] = ws_proxy_call if ws_idx >= 0 else proxy_call
    return FunctionMaker.create(func, "return _call_(%(shortsignature)s)", evaldict)

class _ChannelDict(dict):
    def __missing__(self, key):
        new_ch = Channel(*key)
        self[key] = new_ch
        return new_ch

_channels = _ChannelDict()

@_rpc
def post_update(channel_name, channel_type, message):
    gevent.spawn(_channels[(channel_name, channel_type)].post_message, message)

@_rpc
def subscribe_websocket(channel_name, channel_type, ws, start_from=None):
    _channels[(channel_name, channel_type)].subscribe(ws, start_from)

@_rpc
def unsubscribe_websocket(channel_name, channel_type, ws_id):
    ch = _channels[(channel_name, channel_type)]
    ch.unsubscribe(ch.subscribers[ws_id])

@_rpc
def delete_channel(channel_name, channel_type):
    key = (channel_name, channel_type)
    if key in _channel:
        _channels[key].force_stop()
        del _channels[key]

def _id_cycler(start, end):
    val = start
    while 1:
        yield val
        val += 1

        # The values will be so distant apart that this will probably
        # never happen... But, who knows?
        if val >= end:
            val = start

# Must be called on each worker, before handling websocket connections
def worker_init(worker_id):
    global _worker_count, _ws_id_iterator
    assert worker_id < _worker_count

    total_space = (2 * sys.maxint + 1)
    share = total_space / _worker_count
    start = -sys.maxint - 1 + share * worker_id
    end = start + share

    # Should I just use xrange instead? The gap will be too large
    # for the values to ever warps around (on 64 bits machines).
    _ws_id_iterator = _id_cycler(start, end)

# Must be run on the channels manager process
def rpc_dispatcher():
    global _rpc_map, _call_endpoint, _handle_endpoint

    # Not needed anymore from this process
    _call_endpoint.close()
    del _call_endpoint

    # Dispatch events
    while 1:
        msg, fd = fd_trick.recv_with_fd(_handle_endpoint)
        if fd is not None:
            func_id, args, kwar, ws_locator = pickle.loads(msg)
            if ws_locator is not None:
                args[ws_locator] = _ws_deserialize(fd, args[ws_locator])
            else:
                kwar['ws'] = _ws_deserialize(fd, kwar['ws'])
        else:
            func_id, args, kwar = pickle.loads(msg)
        _rpc_map[func_id](*args, **kwar)

# Must be called before everything in the starter process...
def init(worker_count):
    global _worker_count
    _worker_count = worker_count
