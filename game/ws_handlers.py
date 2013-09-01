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

import datetime
import json

from async_events import channel
from geventwebsocket import WebSocketError
from django.utils.html import escape

def game_events(request, ws, game_id):
    pass

def main_chat(request, ws):
    ws_id = None
    try:
        ws_id = channel.subscribe_websocket('main', ws)
        while 1:
            msg = ws.receive()
            if msg == None:
                break
            msg = msg[2:]

            utcnow = datetime.datetime.utcnow()
            midnight_utc = datetime.datetime.combine(utcnow.date(), datetime.time(0))
            delta = utcnow - midnight_utc

            data = {
                'time_in_sec': delta.seconds,
                'username': 'Desnobro',
                'msg': escape(msg)
            }

            channel.post_update('main', 'c\n' + json.dumps(data))
    except WebSocketError:
        pass
    finally:
        if ws_id is not None:
            channel.unsubscribe_websocket('main', ws_id)
            pass
        print "Done with this websocket..."
