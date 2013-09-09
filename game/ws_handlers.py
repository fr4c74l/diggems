# So, you think you can handle a WebSocket, huh?
# Write you handlers here, and remenber, this ain't no Django view.
# There is no easy ride down here: middlewares doesn't work,
# neither database connection automatically freed for you.

# Each handler is run on its own Greenlet, so make sure you
# release as many resources as possible (like database
# transactions, connections and such) before calling a
# a blocking function (like ws.receive()), so it will not
# disrupt the handling of other requests. Use DBReleaser
# to wrap code that uses database.

import datetime
import json

from async_events import channel
from geventwebsocket import WebSocketError
from django.utils.html import escape
from django.db import transaction, close_connection

from importlib import import_module
from django.conf import settings
SessionStore = import_module(settings.SESSION_ENGINE).SessionStore

from models import UserProfile

# To be used with "with" statement:
# wraps the code in a transaction and releases the database connection afterwards
class DBReleaser(object):
    def __init__(self):
        self._commiter = transaction.commit_on_success()
    
    def __enter__(self):
        self._commiter.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return self._commiter.__exit__(exc_type, exc_value, traceback)
        finally:
            close_connection()

def game_events(request, ws, game_id):
    pass

def main_chat(request, ws):
    try:
        with DBReleaser():
            session = SessionStore(session_key=request.COOKIES['sessionid'])
            profile = UserProfile.get(session)
            username = profile.display_name()

        # First message is the channel register request
        # contains the seqnums per channel type
        msg = ws.receive()
        seq_info = json.loads(msg)['c']
        channel.subscribe_websocket('main', 'c', ws, seq_info['seqnum'], seq_info.get('channel_id'))
        del seq_info
    except KeyError, WebSocketError:
        return

    try:
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
                'username': username,
                'msg': escape(msg)
            }

            channel.post_update('main', 'c', json.dumps(data))
    except WebSocketError:
        pass
    finally:
        try:
            #TODO: inverstigate why sometimes ws.environ is None
            channel.unsubscribe_websocket('main', 'c', ws.environ['unique_id'])
        except KeyError:
            pass
        print "Done with this websocket..."
