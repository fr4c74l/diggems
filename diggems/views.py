# -*- coding: utf-8 -*-
# Copyright 2011 Lucas Clemente Vella
# Software under Affero GPL license, see LICENSE.txt

import itertools
import datetime
import urllib2
import json
import ssl
from wsgiref.handlers import format_date_time
from time import mktime

from django.shortcuts import get_object_or_404, render_to_response
from django.http import *
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.template import Context, RequestContext, loader
from game_helpers import *
from models import *
from https_conn import https_opener

def render_with_extra(template_name, data, request, user):
    t = loader.get_template(template_name)
    c = Context(data)
    if request.is_secure():
        protocol = 'https'
    else:
        protocol = 'http'

    try:
        win_ratio = (float(user.games_won) / user.games_finished) * 100.0
    except ZeroDivisionError:
        win_ratio = None

    extra = {'FB_APP_ID': FB_APP_ID,
             'PROTOCOL': protocol,
             'fb': user.facebook,
             'stats': {'score': user.total_score,
                       'victories': user.games_won,
                       'win_ratio': win_ratio}}
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

    try:
        # TODO: this ideally must be done asyncronuosly...
        res = https_opener.open('https://graph.facebook.com/me?access_token=' + token)
        fb_user = json.load(res)
        res.close()
    except ssl.SSLError:
        # TODO: Log this error? What to do when Facebook
        # connection has been compromised?
        return HttpResponseServerError()

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

    playing_now = Game.objects.filter(Q(p1__user=profile) | Q(p2__user=profile)).exclude(state__gte=3)

    chosen = Game.objects.filter(state__exact=0, token__isnull=True).exclude(p1__user__exact=profile).order_by('?')[:5]
    new_games = []
    for game in chosen:
        info = {'id': game.id}
        player = game.p1.user
        if player.facebook:
            info['op_name'] = player.facebook.name
            info['op_picture'] = ('https://graph.facebook.com/'
                                  + player.facebook.uid
                                  + '/picture')
        else:
            # TODO: internationalization
            info['op_name'] = 'jogador anônimo'

        new_games.append(info)

    context = {'your_games': playing_now, 'new_games': new_games}
    return render_with_extra('index.html', context, request, profile)

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
    p1.save()

    game = Game()
    game.mine = mine_encode(mine)
    if request.REQUEST.get('private', default=False):
        game.token = gen_token()
    game.channel = gen_token()
    game.p1 = p1
    game.save()
    create_channel(game.channel)

    return HttpResponseRedirect('/game/' + str(game.id))

@transaction.commit_on_success
def join_game(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    profile = UserProfile.get(request)

    # If already playing this game, redirect to game screen
    if game.what_player(profile):
        return HttpResponseRedirect('/game/' + str(game.id))

    # If user cannot start this game, then 403
    token = request.REQUEST.get('token')
    if game.state != 0 or (game.token and
                           token != game.token):
        return HttpResponseForbidden()

    # If we got here via GET, return a page that will make the client/user
    # retry via POST. Done so that Facebook and other robots do not join
    # the game in place of a real user.
    if request.method != 'POST':
        url = '/game/' + game_id + '/join/'
        if token:
            url = url + '?token=' + token
        c = Context({'url', url})
        return render_to_response('post_redirect.html', c)

    p2 = Player(user=profile)
    p2.save()

    game.p2 = p2
    game.state = 1
    game.save()

    post_update(game.channel, str(game.seq_num) + '\n' + str(game.state))
    return HttpResponseRedirect('/game/' + game_id)

@transaction.commit_on_success
def game(request, game_id):
    # TODO: maybe control who can watch a game
    game = get_object_or_404(Game, pk=game_id)

    data = {'state': game.state,
            'game_id': game_id,
            'seq_num': game.seq_num,
            'last_change': format_date_time(mktime(datetime.datetime.now().timetuple())),
            'channel': game.channel,
            'p1_last_move': game.p1.last_move}

    if(game.p2):
        data['p2_last_move'] = game.p2.last_move

    profile = UserProfile.get(request)
    pdata = game.what_player(profile)
    if pdata:
        my_number, me = pdata
        data['bomb_used'] = not me.has_bomb
        data['player'] = my_number
        me.save()

    if game.state == 0 and game.token: # Uninitialized private game
        data['token'] = game.token
    else:
        masked = mine_mask(game.mine, game.state > 2)
        if masked.count('?') != 256:
            data['mine'] = masked

    return render_with_extra('game.html', data, request, profile)

@transaction.commit_on_success
def move(request, game_id):
    game = get_object_or_404(Game, pk=game_id)

    pdata = game.what_player(UserProfile.get(request))
    if not pdata or pdata[0] != game.state:
        return HttpResponseForbidden()

    player, me = pdata

    try:
        m = int(request.GET['m'])
        n = int(request.GET['n'])
        if not (0 <= m <= 15 and 0 <= n <= 15):
            raise ValueError
    except:
        return HttpResponseBadRequest()

    mine = mine_decode(game.mine)

    to_reveal = [(m, n)]
    bomb_used = False

    if request.GET.get('bomb') == 'y':
        if not me.has_bomb:
            return HttpResponseBadRequest()
        me.has_bomb = False
        to_reveal = itertools.product(xrange(max(m-2,0),
                                             min(m+3, 16)),
                                      xrange(max(n-2,0),
                                             min(n+3, 16)))
        bomb_used = True

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

    for x, y in to_reveal:
        reveal(x, y)

    if not revealed:
        return HttpResponseBadRequest()

    if mine[m][n] <= 18 or bomb_used:
        game.state = (game.state % 2) + 1

    new_mine = mine_encode(mine)
    points = [new_mine.count(tile_encode(19)), new_mine.count(tile_encode(20))]

    if points[0] >= 26 or points[1] >= 26:
        game.state = player + 2

    coded_move = '%s%x%x' % ('b' if bomb_used else 'd', m, n)
    me.last_move = coded_move
    game.mine = new_mine
    game.save()
    me.save()

    if game.state >= 3: # Game is over
        remaining = 51 - points[0] - points[1]
        points[0 if points[0] > points[1] else 1] += remaining

        for user, idx in ((game.p1.user, 0), (game.p2.user, 1)):
            user.games_finished = F('games_finished') + 1
            user.total_score = F('total_score') + points[idx]
            if game.state == (idx + 3):
                user.games_won = F('games_won') + 1

            user.save()

        for m, n in itertools.product(xrange(0, 16), xrange(0, 16)):
             if mine[m][n] == 9:
                 revealed.append((m, n, 'x'))

    result = str(game.seq_num) + '\n' + str(game.state) + '\n' + str(player) + '\n' + coded_move + '\n' + '\n'.join(map(lambda x: '%d,%d:%c' % x, revealed))

    # Since updating Facebook with score may be slow, we post
    # the update to the user now...
    post_update(game.channel, result)

    # ... and then publish the scores on FB, if game is over.
    # (TODO: If only this could be done asyncronously...)
    if game.state >= 3: 
        publish_score(game.p1.user)
        publish_score(game.p2.user)

    return HttpResponse()
