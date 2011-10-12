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

EVENT_SERVER = '127.0.0.1'
FB_APP_ID = '264111940275149'
FB_APP_KEY = '8a9260360907fd0cdffc1deafeb16b24'

def tile_encode(tile):
    return chr(tile + 10)

def mine_encode(mine):
    mine = itertools.chain.from_iterable(mine)
    mine = map(tile_encode, mine)
    return ''.join(mine)

def tile_decode(tile):
    return ord(tile) - 10

def mine_decode(encoded):
    mine = [[0] * 16 for i in xrange(16)]
    for i, (m, n) in zip(xrange(256), itertools.product(xrange(16), repeat=2)):
        mine[m][n] = tile_decode(encoded[i])
    return mine

def tile_mask(n):
        if n < 10:
            return '?'
        elif n < 19:
            return str(n - 10)
        elif n == 19:
            return 'r'
        else:
            return 'b'

def mine_mask_encoded(mine):
    return ''.join(map(lambda t: tile_mask(tile_decode(t)), mine))

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

def inc_score(user, ammount):
    user.total_score = F('total_score') + ammount
    user.save()
    user = models.UserProfile.objects.get(pk=user.pk)

    def publish_score():
        if user.facebook:
            # Publish score...
            # TODO: verify HTTPS
            # TODO: make it asyncronous
            app_token = cache.get('app_token')
            if not app_token:
                try:
                    app_token = urllib2.urlopen('https://graph.facebook.com/oauth/access_token?client_id=' + FB_APP_ID + '&client_secret=' + FB_APP_KEY + '&grant_type=client_credentials').read()
                    cache.set('app_token', app_token, 3600)
                except urllib2.HTTPError:
                    # TODO: Log error before returning...
                    return
            # There is a small chance that a race condition will make the score
            # stored at Facebook to be inconsistent. But since it is temporary
            # until the next game play, the risk seems acceptable.
            urllib2.urlopen('https://graph.facebook.com/' + user.facebook.uid + '/scores', 'score=' + str(user.total_score) + '&' + app_token).read()

    try:
        publish_score()
    except urllib2.HTTPError:
        # App access token must have expired, try just once more
        cache.delete('app_token')
        publish_score()

# Event dealing:
def create_channel(channel):
    try:
        conn = httplib.HTTPConnection(EVENT_SERVER)
        conn.request('PUT', '/ctrl_event?id=' + channel,
                     headers={'Content-Length': 0})
        resp = conn.getresponse()
    except:
        pass # TODO: log error

def delete_channel(channel):
    try:
        conn = httplib.HTTPConnection(EVENT_SERVER)
        conn.request('DELETE', '/ctrl_event?id=' + channel)
        resp = conn.getresponse()
    except:
        pass # TODO: log error

def post_update(channel, msg):
    try:
        conn = httplib.HTTPConnection(EVENT_SERVER)
        conn.request('POST', '/ctrl_event?id=' + channel, msg,
                     headers={'Content-Type': 'text/plain'})
        resp = conn.getresponse()
    except:
        pass # TODO: log error

