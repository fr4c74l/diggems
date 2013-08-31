# So, you think you can handle a WebSocket, huh?
# Write you handlers here, and remenber, this ain't no Django view.
# There is no easy ride down here: middlewares doesn't work,
# neither database connection are set and ready waiting for you.

# Each handler is run on its own Greenlet, so make sure you
# release as many resources as possible (like database
# transactions, connections and such) before calling a
# a blocking function (like ws.receive()), so it will not
# disrupt the handling of other requests.

# TODO: Find out how to deal with database and auth cookies and stuff...

from geventwebsocket import WebSocketError

def game_events(request, ws, game_id):
    pass

def main_chat(request, ws):
    try:
        while 1:
            ret = ws.receive()
            if ret:
                break
    finally:
        print "Done with this websocket..."
