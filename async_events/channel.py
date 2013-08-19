import gevent
import gipc

class Channel(object):
    def __init__(self):
        self.seqnum = 0

    def register_channel(self, starting_point, ws):
        pass

_workers2channel = None
_channel2workers = None

_rpc_map = {}
_rpc_next_id = 0

def _rpc(func):
    global _workers2channel, _rpc_next_id, _rpc_map
    func_id = _rpc_next_id
    _rpc_next_id += 1
    
    _rpc_map[func_id] = func

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

# Must be called on each worker, for it to receive websockets and listen to them
def websocket_acceptor(worker_id, ws_handler):
    global _channel2workers
    from_channel = _channel2workers[worker_id][0]

    # Close uneeded pipes
    for r, w in _channel2workers:
        w.close()
        if from_channel != r:
            r.close()
    del _channel2workers

    while 1:
        ws = None # TODO: black magic to receive websockt from another process
    
        headers = None # TODO: find out how to have the cookie headers to identify the user
    
        gevent.spawn(ws_handler, ws, headers)

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

# Must be called before everything in the starter process, to create the shared pipes
def init(worker_count):
    global _workers2channel, _channel2workers
    _workers2channel = gipc.pipe()

    _channel2workers = [gipc.pipe() for i in xrange(worker_count)]
