import gevent
import gipc
import weakref
import sys

class Channel(object):
    def __init__(self):
        self.seqnum = 0

    def register_channel(self, starting_point, ws):
        pass

_ws_refs = weakref.WeakValueDictionary()

# To generate new ids for websocket on worker (warps after trillons of years):
_ws_id_iterator = None 

_worker_count = 1

_workers2channel = gipc.pipe()

_rpc_map = {}
_rpc_next_id = 0

def _rpc(func):
    global _workers2channel, _rpc_next_id, _rpc_map
    func_id = _rpc_next_id
    _rpc_next_id += 1
    
    _rpc_map[func_id] = func

    # TODO: to be continued: treat special case of marked websocket parameters

    def proxy_call(*args, **kwar):
        msg = (func_id, args, kwar)
        _workers2channel[1].put(msg)
        # No return value allowed
    return proxy_call

@_rpc
def create_channel(channel_name):
    pass # TODO

@_rpc
def delete_channel(channel_name):
    pass # TODO

@_rpc
def post_update(channel_name, message):
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
    global _rpc_map, _workers2channel
    receiver = _workers2channel[0]

    # Not needed anymore from this process
    _workers2channel[1].close()
    del _workers2channel

    # Dispatch events
    while 1:
        (func_id, args, kwar) = receiver.get()
        _rpc_map[func_id](*args, **kwar)

# Must be called before everything in the starter process...
def init(worker_count):
    global _worker_count
    _worker_count = worker_count
