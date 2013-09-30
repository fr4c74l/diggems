# Copyright 2011 Lucas Clemente Vella
# Software under Affero GPL license, see LICENSE.txt

import itertools
import models
import http_cli
import urllib2
import json
from http_cli import get_conn
from django.core.cache import cache
from django.db.models import F
from diggems.settings import EVENT_SERVER, FB_APP_ID, FB_APP_KEY

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

def fb_ograph_call(func):
    conn = get_conn('https://graph.facebook.com')
    class CacheMiss(Exception):
        pass
    try:
        app_token = cache.get('app_token')
        if app_token is None:
            raise CacheMiss()
        ret = func(conn, app_token)
    except urllib2.HTTPError, CacheMiss:
        try:
            with conn.get('/oauth/access_token?client_id={}&client_secret={}&grant_type=client_credentials'.format(FB_APP_ID, FB_APP_KEY)) as req:
                app_token = req.read()
                cache.set('app_token', app_token, 3600)
        except urllib2.HTTPError:
            # TODO: Log error before returning...
            return
        ret = func(conn, app_token)
    return json.loads(ret)

def publish_score(user):
    def try_publish_score(conn, app_token):
        # There is a small chance that a race condition will make the score
        # stored at Facebook to be inconsistent. But since it is temporary
        # until the next game play, the risk seems acceptable.
        with conn.post('/{}/scores'.format(user.facebook.uid), 'score={}&{}'.format(user.total_score, app_token)) as req:
            req.read() # Ignore return value, because there is not much we can do with it...
    
    fb_ograph_call(try_publish_score)
