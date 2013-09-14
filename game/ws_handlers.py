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
from django.utils.translation import ugettext as _
from django.core.exceptions import ObjectDoesNotExist

from importlib import import_module
from django.conf import settings
SessionStore = import_module(settings.SESSION_ENGINE).SessionStore

import models

# To be used with "with" statement:
# wraps the code in a transaction and releases the database connection afterwards
class DBReleaser(object):
    __slots__ = ('_commiter',)
    def __init__(self):
        self._commiter = transaction.commit_on_success()
    
    def __enter__(self):
        self._commiter.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return self._commiter.__exit__(exc_type, exc_value, traceback)
        finally:
            close_connection()

class ChannelRegisterer(object):
    __slots__ = ('chname', 'types', 'ws')
    def __init__(self, ws, name, types):
        self.chname = name
        self.types = types
        self.ws = ws

    def __enter__(self):
        try:
            # First message is the channel register request
            # contains the seqnums per channel type
            msg = self.ws.receive()
            seq_infos = json.loads(msg)
            print seq_infos
            for t in self.types:
                seq_info = seq_infos[t]
                seqnum = seq_info['seqnum']
                channid = seq_info.get('channel_id')
                channel.subscribe_websocket(self.chname, t, self.ws, seqnum, channid)
        except:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            #TODO: inverstigate why sometimes ws.environ is None
            ws_id = self.ws.environ['unique_id']
            for t in self.types:
                channel.unsubscribe_websocket(self.chname, t, ws_id)
        except KeyError:
            pass

        return exc_type == WebSocketError

def day_seconds():
    utcnow = datetime.datetime.utcnow()
    midnight_utc = datetime.datetime.combine(utcnow.date(), datetime.time(0))
    delta = utcnow - midnight_utc
    return delta.seconds

def report_chat_event(chname, username, connection):
    if connection:
        status = _('{} joined the chat')
    else:
        status = _('{} has left the chat')

    data = {
        'time_in_sec': day_seconds(),
        'status': status.format(username)
    }
    channel.post_update(chname, 'c', json.dumps(data))

def chat_post(chname, username, msg):
    data = {
        'time_in_sec': day_seconds(),
        'username': username,
        'msg': escape(msg)
    }

    channel.post_update(chname, 'c', json.dumps(data))

def chat_loop(ws, chname, types, username):
    try:
        with ChannelRegisterer(ws, chname, types):
            report_chat_event(chname, username, True)
            while 1:
                msg = ws.receive()
                if msg == None:
                    break
                msg = msg[2:]
                chat_post(chname, username, msg)
    finally:
        report_chat_event(chname, username, False)

def game_events(request, ws, game_id):
    with DBReleaser():
        try:
            game = models.Game.objects.get(pk=game_id)
            session = SessionStore(session_key=request.COOKIES['sessionid'])
            profile = models.UserProfile.get(session)
            #pdata = game.what_player(profile)
            username = profile.display_name()
        except ObjectDoesNotExist:
            return

    # TODO: implement user connect/disconnect state tracker...
    chname = 'g' + str(game_id)
    chat_loop(ws, chname, 'cgp', username)

def main_chat(request, ws):
    with DBReleaser():
        try:
            session = SessionStore(session_key=request.COOKIES['sessionid'])
            profile = models.UserProfile.get(session)
            username = profile.display_name()
        except ObjectDoesNotExist:
            return

    chat_loop(ws, 'main', 'c', username)
