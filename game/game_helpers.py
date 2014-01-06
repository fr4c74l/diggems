# Copyright 2011 Lucas Clemente Vella
# Software under Affero GPL license, see LICENSE.txt

import itertools
import models
import http_cli
import urllib2
import json
import gevent
from async_events import channel
from functools import partial
from http_cli import get_conn
from django.utils.http import urlencode
from django.core.cache import cache
from django.db.models import F
from diggems.settings import FB_APP_ID, FB_APP_KEY

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

def update_elo_rank(winner, loser):
    winner_rank, loser_rank = winner.elo, loser.elo
    rank_diff = winner_rank - loser_rank
    expectation = -(rank_diff / 400.0)
    winner_odds = 1.0 / (1 + (10**expectation))

    # IECC uses the following kfactor ranges
    if winner_rank <= 2100:
        kfactor = 32
    elif winner_rank > 2100 and winner_rank < 2400:
        kfactor = 24
    else:
        kfactor = 16

    # Rnew = Roriginal + Kfactor(score - expectations)
    new_winner_rank = int(round(winner_rank + (kfactor * (1 - winner_odds))))
    new_rank_diff = new_winner_rank - winner_rank
    new_loser_rank  = loser_rank - new_rank_diff

    if new_loser_rank < 1:
        new_loser_rank = 1

    winner.elo = new_winner_rank
    loser.elo = new_loser_rank

def endgame(winner, loser, game_state):
    if game_state == 3 or game_state == 5:
        update_elo_rank(winner, loser)
    elif game_state == 4 or game_state == 6:
        update_elo_rank(loser, winner)

def notify_open_game(game_ready=False):
    if not game_ready:
        game_ready = models.Game.objects.filter(state__exact=0, token__isnull=True).exists()

    cached = cache.get('game_ready')
    if game_ready != cached:
        data = json.dumps({'game_ready': game_ready})
        channel.post_update('main', 'i', data)
        cache.set('game_ready', game_ready, 3600)

def fb_ograph_call(func):
    conn = get_conn('https://graph.facebook.com')
    class CacheMiss(Exception):
        pass
    try:
        app_token = cache.get('app_token')
        if app_token is None:
            raise CacheMiss()
        return func(conn, app_token)
    except (urllib2.HTTPError, CacheMiss):
        try:
            with conn.get('/oauth/access_token?client_id={}&client_secret={}&grant_type=client_credentials'.format(FB_APP_ID, FB_APP_KEY)) as req:
                app_token = req.read()
                cache.set('app_token', app_token, 3600)
        except urllib2.HTTPError:
            # TODO: Log error before returning...
            return
        return func(conn, app_token)

def publish_score(user):
    def try_publish_score(conn, app_token):
        # There is a small chance that a race condition will make the score
        # stored at Facebook to be inconsistent. But since it is temporary
        # until the next game play, the risk seems acceptable.
        with conn.post('/{}/scores'.format(user.facebook.uid), 'score={}&{}'.format(user.total_score, app_token)) as req:
            req.read() # Ignore return value, because there is not much we can do with it...

    if user.facebook:
        gevent.spawn(fb_ograph_call, try_publish_score)

def start_cancel_request(fb_request):
    calls = ({'method': 'DELETE', 'relative_url': '_'.join((fb_request.id, uid))} for uid in fb_request.targets)

    def del_request_batch(batch, conn, app_token):
        with conn.post('/', '&'.join((urlencode({'batch': batch}), app_token))) as req:
            req.read() # Just ignore return value

    # Facebook rules that there must be no more than 50 requests per batch,
    # so we split it in multiple requests if doesn't fit in a single
    while True:
        batch = list(itertools.islice(calls, 50))
        if not batch:
            break
        if len(batch) == 1:
            def del_single_request(conn, app_token):
                with conn.delete('/{}?{}'.format(batch[0]['relative_url'], app_token)) as req:
                    req.read()
            gevent.spawn(fb_ograph_call, del_single_request)
            break
        batch = json.dumps(batch)
        call = partial(del_request_batch, batch)
        gevent.spawn(fb_ograph_call, call)
