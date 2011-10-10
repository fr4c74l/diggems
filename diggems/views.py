# Copyright 2011 Lucas Clemente Vella
# Software under Affero GPL license, see LICENSE.txt

import itertools
import datetime
import urllib2
import json
from wsgiref.handlers import format_date_time
from time import mktime

from django.shortcuts import get_object_or_404
from django.http import *
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.template import Context, RequestContext, loader
from game_helpers import *
from models import *
from https_conn import secure_url_opener

FB_APP_ID = '264111940275149'

def render_with_extra(template_name, data, request, user):
    t = loader.get_template(template_name)
    c = Context(data)
    if request.is_secure():
        protocol = 'https'
    else:
        protocol = 'http'
    extra = {'FB_APP_ID': FB_APP_ID,
             'PROTOCOL': protocol,
             'fb': user.facebook}
    c.update(extra)
    return HttpResponse(t.render(c))

def fb_channel(request):
    resp = HttpResponse('<script src="//connect.facebook.net/pt_BR/all.js"></script>')
    secs = 60*60*24*365
    resp['Pragma'] = 'public'
    resp['Cache-Control'] = 'max-age=' + str(secs)
    far_future = (datetime.datetime.now() + datetime.timedelta(seconds=secs))
    resp['Expires'] = format_date_time(mktime(far_future.timetuple()))
    return resp

@transaction.commit_on_success
def fb_login(request):
    token = request.POST.get('token')
    expires = request.POST.get('expires')
    if not (token and expires):
        return HttpResponseBadRequest()

    expires = (datetime.datetime.now() +
                  datetime.timedelta(seconds=(int(expires) - 10)))

    # TODO: this ideally must be done asyncronuosly...

    # TODO: Fix this damn secure connection that can not verify Facebook's
    # certificate...
    #url_opener = secure_url_opener()
    #res = url_opener.open('https://graph.facebook.com/me?access_token=' + token)
    res = urllib2.urlopen('https://graph.facebook.com/me?access_token=' + token)
    fb_user = json.load(res)
    res.close()

    try:
        fb = FacebookCache.objects.get(uid=fb_user['id'])
    except FacebookCache.DoesNotExist:
        fb = FacebookCache(uid=fb_user['id'])

    fb.name = fb_user['name']
    fb.access_token = token
    fb.expires = expires
    fb.save()

    old_user_id = request.session.get('user_id')
    try:
        profile = UserProfile.objects.get(facebook=fb)
        if old_user_id and old_user_id != profile.id:
            try:
                old_profile = UserProfile.objects.get(pk=old_user_id)
                if not old_profile.user and not old_profile.facebook:
                    profile.merge(old_profile)
            except UserProfile.DoesNotExist:
                pass

    except UserProfile.DoesNotExist:
        try:
            profile = UserProfile.objects.get(pk=old_user_id)
            if not profile.user and not profile.facebook:
                profile.facebook = fb
            else:
                profile = UserProfile(id=gen_token(), facebook=fb)
        except UserProfile.DoesNotExist:
            profile = UserProfile(id=gen_token(), facebook_id=fb_user.id)
    profile.save()

    request.session['user_id'] = profile.id

    t = loader.get_template('auth_fb.json')
    c = Context({'fb': fb})
    return HttpResponse(t.render(c), mimetype='application/json')

@transaction.commit_on_success
def fb_logout(request):
    profile = UserProfile.get(request)
    if profile.user or profile.facebook:
        profile = UserProfile(id=gen_token())
        profile.save()
        request.session['user_id'] = profile.id

    return HttpResponse()

def index(request):
    profile = UserProfile.get(request)

    playing_now = Game.objects.filter(Q(p1__user=profile) |
                                      Q(p2__user=profile))

    return render_with_extra('index.html', {'games': playing_now},
                             request, profile)

@transaction.commit_on_success
def new_game(request):
    if request.method != 'POST':
        return HttpResponseForbidden()

    profile = UserProfile.get(request)

    mine = [[0] * 16 for i in xrange(16)]

    indexes = list(itertools.product(xrange(16), repeat=2))
    gems = random.sample(indexes, 51)

    for (m, n) in gems:
        mine[m][n] = 9

    for m, n in indexes:
        if mine[m][n] == 0:
            def inc_count(x, y):
                if mine[x][y] == 9:
                    mine[m][n] += 1
            for_each_surrounding(m, n, inc_count)

    p1 = Player(user=profile)
    p1.channel = gen_token()
    p1.save()
    create_channel(p1.channel)

    game = Game()
    game.mine = mine_encode(mine)
    game.token = gen_token()
    game.p1 = p1
    game.private = bool(request.REQUEST.get('private', default=False))
    game.save()

    return HttpResponseRedirect('/game/' + str(game.id))

@transaction.commit_on_success
def join_game(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    profile = UserProfile.get(request)

    if game.what_player(profile):
        return HttpResponseRedirect('/game/' + str(game.id))

    if game.state != 0 or request.REQUEST.get('token') != game.token:
        return HttpResponseForbidden()

    p2 = Player(user=profile)
    p2.channel = gen_token()
    p2.save()
    create_channel(p2.channel)

    game.p2 = p2
    game.state = 1
    game.save()

    post_update(game.p1.channel, str(game.seq_num) + '\n' + str(game.state))
    return HttpResponseRedirect('/game/' + game_id)

def game(request, game_id):
    game = get_object_or_404(Game, pk=game_id)

    profile = UserProfile.get(request)
    pdata = game.what_player(profile)
    if not pdata:
        return HttpResponseForbidden()
    player, me, other = pdata

    data = {'state': game.state,
            'game_id': game_id,
            'seq_num': game.seq_num,
            'last_change': format_date_time(mktime(datetime.datetime.now().timetuple())) }

    data['bomb_used'] = not me.has_bomb
    data['channel'] = me.channel
    data['player'] = player

    if game.state == 0: # Uninitialized game
        data['token'] = game.token
    else:
        masked = mine_mask_encoded(game.mine)
        if masked.count('?') != 256:
            data['mine'] = masked

    me.save()

    return render_with_extra('game.html', data, request, profile)

def move(request, game_id):
    game = get_object_or_404(Game, pk=game_id)

    pdata = game.what_player(UserProfile.get(request))
    if not pdata or pdata[0] != game.state:
        return HttpResponseForbidden()

    player, me, other = pdata

    try:
        m = int(request.GET['m'])
        n = int(request.GET['n'])
        if not (0 <= m <= 15 and 0 <= n <= 15):
            raise ValueError
    except:
        return HttpResponseBadRequest()

    mine = mine_decode(game.mine)

    if request.GET.get('bomb') == 'y':
        if not me.has_bomb:
            return HttpResponseBadRequest()
        me.has_bomb = False
        m0 = max(m-2, 0)
        m5 = min(m+2, 15)
        to_reveal = itertools.product(xrange(max(m-2,0),
                                             min(m+3, 16)),
                                      xrange(max(n-2,0),
                                             min(n+3, 16)))
        bomb_used = True
    else:
        to_reveal = [(m, n)]
        bomb_used = False

    revealed = []
    def reveal(m, n):
        if mine[m][n] >= 10:
            return

        old = mine[m][n]
        mine[m][n] += 10
        if mine[m][n] == 19 and player == 2:
            mine[m][n] = 20
        revealed.append((m, n, tile_mask(mine[m][n])))
        if old == 0:
            for_each_surrounding(m, n, reveal)

    for m, n in to_reveal:
        reveal(m, n)

    if not revealed:
        return HttpResponseBadRequest()

    m, n, s = revealed[0]
    if mine[m][n] <= 18 or bomb_used:
        game.state = (game.state % 2) + 1

    new_mine = mine_encode(mine)
    point_p1 = new_mine.count(tile_encode(19))
    point_p2 = new_mine.count(tile_encode(20))

    if point_p1 >= 26 or point_p2 >= 26:
        game.state = player + 2

    game.mine = new_mine
    game.save()

    result = str(game.seq_num) + '\n' + str(game.state) + '\n' + '\n'.join(map(lambda x: '%d,%d:%c' % x, revealed))

    post_update(other.channel, result)
    if game.state >= 3: # Game is over
        game.p1.delete()
        game.p2.delete()
    else:
        me.save()

    return HttpResponse(result, mimetype='text/plain')
