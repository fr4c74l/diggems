import gevent
import gipc

class Channel(object):
    pass # TODO

_from_workers = None
_workers_endpoint = None

_rpc_map = {}
_rpc_next_id = 0

def _rpc(func):
    global _rpc_next_id, _rpc_map
    func_id = _rpc_next_id
    _rpc_next_id += 1
    
    _rpc_map[func_id] = func

    def proxy_call(*args, **kwar):
        msg = (func_id, args, kwar)
        _workers_endpoint.put(msg)
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
    while 1:
        ws = None # TODO: black magic to receive websockt from another process
    
        headers = None # TODO: find out how to have the cookie headers to identify the user
    
        gevent.spawn(ws_handler, ws, headers)

# Must be run on the channels manager process
def serve_forever(sock_name):
    def rpc_caller():
        global _rpc_map
        while 1:
            (func_id, args, kwar) = from_workers.get()
            _rpc_map[func_id](*args, **kwar)
    gevent.spawn(rpc_caller)

    # TODO: gevent websocket server
    # and black magic to handle each to a worker

# Must be called before everything in the starter process, to create the shared pipes
def init(worker_count):
    global _from_workers, _workers_endpoint
    (_from_workers, _workers_endpoint) = gipc.pipe()
    
    # TODO: communication pipes for each worker
