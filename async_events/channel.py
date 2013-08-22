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

class _Subscriber(object):
    def __init__(self, ws):
        self.ws = ws
        self.deliverer = None

        # Node
        self.prev = None
        self.next = None

class _ListHead(object):
    def __init__(self):
        self.next = None

class Channel(object):
    def __init__(self):
        self.next_seqnum = 0
        self.first_seqnum = 0
        self.msg_history = {}
        self.subscribers = {}

        # Linked lists...
        self.delivering = _ListHead()
        self.waiting = _ListHead()

    def subscribe(self, ws, from_seqnum=None):
        sb = _Subscriber(ws)
        self.subscribers[ws.unique_id] = sb
        if from_seqnum and self.next_seqnum > from_seqnum:
            sb.deliverer = gevent.spawn(self._deliver, sb, from_seqnum)
            place = self.delivering
        else:
            place = self.waiting
        self._node_attach(place, sb)

    def unsubscribe(self, ws_id):
        pass

    def post_message(self, msg):
        msg = struct.pack("<Hi") #... continue
        # TODO: format message to be ready to send
        pass

    def _deliver(self, sb, seqnum):
        ws = sb.ws
        while seqnum < self.next_seqnum:
            if seqnum < self.first_seqnum:
                seqnum = self.first_seqnum
            msg = self.msg_history[seqnum]
            ws.send(msg)
            seqnum += 1

        sb.deliver = None
        self._node_detach(sb)
        self._node_attach(self.waiting, node)

    @staticmethod
    def _node_detach(at, node):
        node.prev.next = node.next
        if node.next:
            node.next.prev = node.prev

    @staticmethod
    def _node_attach(at, node):
        node.next = at.next
        node.prev = at
        if at.next:
            at.next.prev = node
        at.next = node
    

_ws_refs = weakref.WeakValueDictionary()

# To generate new ids for websocket on worker (warps after trillons of years):
_ws_id_iterator = None 

_worker_count = 1

_rpc_map = {}
_rpc_next_id = 0

(_call_endpoint, _handle_endpoint) = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)

def _ws_serialize(websocket):
    try:
        uid = websocket.unique_id
    except AttributeError:
        uid = _ws_id_iterator.next()
        websocket.unique_id = uid

    return (websocket.handler.socket.fileno(), uid)

def _ws_from_fd(fd):
    class RecvStream(object):
        __slots__ = ('read', 'write')
    
        def __init__(self, handler):
            self.sock = socket.fromfd(handler, socket.AF_INET, socket.SOCK_STREAM)
            self.write = self.sock.sendall
            self.buf = None
            self.offset = 0
    
        def read(self, size):
            raise NotImplementedError("I didn't expect reads to occur from this copy of the socket...")

    class PseudoHandler(object):
        def __init__(self, fd):
            self.logger = create_logger('ws_'.format(fd), DEBUG)

    return WebSocket(None, RecvStream(fd), PseudoHandler(fd))

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
        if ret != len(message):
            # TODO: Weird! Can this ever happen? Maybe if message is too big.
            # Do something about it...
            pass

    def proxy_call(*args, **kwar):
        msg = pickle.dumps((func_id, args, kwar), pickle.HIGHEST_PROTOCOL)
        ret = _call_endpoint.send(msg)
        if ret != len(message):
            # TODO: Weird! Can this ever happen? Maybe if message is too big.
            # Do something about it...
            pass

    # Have no ideia of how this works, just copied from decorator.py:
    evaldict = func.func_globals.copy()
    evaldict['_call_'] = ws_proxy_call if ws_idx >= 0 else proxy_call
    return FunctionMaker.create(func, "return _call_(%(shortsignature)s)", evaldict)

@_rpc
def create_channel(channel_name):
    pass # TODO

@_rpc
def delete_channel(channel_name):
    pass # TODO

@_rpc
def post_update(channel_name, message):
    pass # TODO

@_rpc
def register_websocket(channel_name, ws, start_from=None):
    pass # TODO

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
        msg, fd = fd_trick.recv_with_fd(_call_endpoint)
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
