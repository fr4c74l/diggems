# Copyright 2011 Lucas Clemente Vella
# Software under Affero GPL license, see LICENSE.txt

import urllib2
import itertools
import random
import httplib
import radix64
import models
from django.core.cache import cache
from django.db.models import F
from https_conn import https_opener

EVENT_SERVER = '127.0.0.1'
FB_APP_ID = '264111940275149'
FB_APP_KEY = '8a9260360907fd0cdffc1deafeb16b24'

## Tile codes:
# 0     -> empty hidden tile
# 1-8   -> hidden clue of 1-8 surrounding gems
# 9     -> hidden gem
# 10    -> empty exposed tile
# 11-18 -> exposed clue
# 19    -> gem found by player 1 (red)
# 20    -> gem found by player 2 (blue)

# Encode a tile code into a character to be stored in DB
def tile_encode(tile):
    return chr(tile + 10)

# Encode a matrix of tile codes into a string to be stored in DB
def mine_encode(mine):
    mine = itertools.chain.from_iterable(mine)
    mine = map(tile_encode, mine)
    return ''.join(mine)

# Decode a character stored in DB back to a tile code
def tile_decode(tile):
    return ord(tile) - 10

# Decode a mine string stored in DB back into a matrix of tile codes
def mine_decode(encoded):
    mine = [[0] * 16 for i in xrange(16)]
    for i, (m, n) in zip(xrange(256), itertools.product(xrange(16), repeat=2)):
        mine[m][n] = tile_decode(encoded[i])
    return mine

# Encode tile to client-side symbols
def tile_mask(n, revealed=False):
        if n < 9:
            return '?'
        elif n == 9:
            return ('x' if revealed else '?')
        elif n < 19:
            return str(n - 10)
        elif n == 19:
            return 'r'
        else:
            return 'b'

# Encode a full mine database string to client-side symbols
def mine_mask(mine, revealed):
    return ''.join(map(lambda t: tile_mask(tile_decode(t), revealed), mine))

def for_each_surrounding(m, n, func):
    surroundings = ((-1,-1),(-1, 0),(-1, 1),
                    ( 0,-1),        ( 0, 1),
                    ( 1,-1),( 1, 0),( 1, 1))

    for (dx, dy) in surroundings:
        x = m + dx
        y = n + dy
        if 0 <= x <= 15 and 0 <= y <= 15:
            func(x, y)

def gen_token():
    return radix64.encode(random.getrandbits(132))

def publish_score(user):
    def try_publish_score():
        # Publish score...
        # TODO: log Facebook connection error, but do not raise exception
        # TODO: make it asyncronous
        app_token = cache.get('app_token')
        if not app_token:
            try:
                app_token = https_opener.open('https://graph.facebook.com/oauth/access_token?client_id=' + FB_APP_ID + '&client_secret=' + FB_APP_KEY + '&grant_type=client_credentials').read()
                cache.set('app_token', app_token, 3600)
            except urllib2.HTTPError:
                # TODO: Log error before returning...
                return
        # There is a small chance that a race condition will make the score
        # stored at Facebook to be inconsistent. But since it is temporary
        # until the next game play, the risk seems acceptable.
        https_opener.open('https://graph.facebook.com/' + user.facebook.uid + '/scores', 'score=' + str(user.total_score) + '&' + app_token).read()

    if user.facebook:
        # Reload to ensure most accurate score
        user = models.UserProfile.objects.get(pk=user.pk)
        try:
            try_publish_score()
        except urllib2.HTTPError:
            # App access token must have expired, try just once more
            cache.delete('app_token')
            try_publish_score()

# Event dealing:
def create_channel(channel):
    try:
        conn = httplib.HTTPConnection(EVENT_SERVER)
        conn.request('PUT', '/ctrl_event/' + channel,
                     headers={'Content-Length': 0})
        resp = conn.getresponse()
    except:
        pass # TODO: log error

def delete_channel(channel):
    try:
        conn = httplib.HTTPConnection(EVENT_SERVER)
        conn.request('DELETE', '/ctrl_event/' + channel)
        resp = conn.getresponse()
    except:
        pass # TODO: log error

def post_update(channel, msg):
    try:
        conn = httplib.HTTPConnection(EVENT_SERVER)
        conn.request('POST', '/ctrl_event/' + channel, msg,
                     headers={'Content-Type': 'text/plain'})
        resp = conn.getresponse()
    except:
        pass # TODO: log error

