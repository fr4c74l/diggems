# -*- coding: utf-8 -*-
# Copyright 2011 Lucas Clemente Vella
# Software under Affero GPL license, see LICENSE.txt

import itertools
import datetime
import json
import ssl
import gevent
import http_cli
import hashlib
import locale
import gevent
from functools import partial
from django.conf import settings
from wsgiref.handlers import format_date_time
from time import mktime
from datetime import datetime, time

from django.shortcuts import get_object_or_404, render_to_response
from django.template.response import SimpleTemplateResponse
from django.http import *
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.template import Context, RequestContext, loader, TemplateDoesNotExist
from django.template.defaultfilters import floatformat
from django.utils.html import escape, mark_safe
from django.utils.http import urlquote, urlencode
from django.utils.translation import pgettext
from django.core.exceptions import ObjectDoesNotExist
from models import *
from diggems.utils import gen_token, true_random
from django.utils.translation import to_locale, get_language
from game_helpers import *
from async_events import channel

def get_user_info(user, with_private=False):
    if user.facebook:
        info = {
            'name': user.facebook.name,
            'pic_url': '//graph.facebook.com/{}/picture'.format(user.facebook.uid),
            'profile_url': '//facebook.com/{}/'.format(user.facebook.uid)
        }
        if with_private:
            info['auth'] = {'fb': {'uid': user.facebook.uid}}
    else:
        info = {
            'name': user.guest_name(),
            'pic_url': '//www.gravatar.com/avatar/{}.jpg?d=identicon'.format(hashlib.md5(user.id).hexdigest()),
        }

    # For now, score info is private
    if with_private:
        stats = {
            'score': user.total_score,
            'victories': user.games_won,
        }

        try:
            stats['win_ratio'] = floatformat((float(user.games_won) / user.games_finished) * 100.0)
        except ZeroDivisionError:
            pass

        info['stats'] = stats

    return info

def render_with_extra(template_name, user, data={}, status=200):
    data['user'] = get_user_info(user, True)
    return SimpleTemplateResponse(template_name, data, status=status)

def fb_channel(request):
    resp = HttpResponse(
        '<script src="//connect.facebook.net/{}/all.js"></script>'.format(pgettext("Facebook", "en_US")),
        content_type='text/html')
    secs = 60*60*24*365
    resp['Pragma'] = 'public'
    resp['Cache-Control'] = 'max-age=' + str(secs)
    far_future = (datetime.datetime.now() + datetime.timedelta(seconds=secs))
    resp['Expires'] = format_date_time(mktime(far_future.timetuple()))
    return resp

@transaction.commit_on_success
def fb_login(request):
    token = request.POST.get('token')
    if not token:
        return HttpResponseBadRequest()

    try:
        with http_cli.get_conn('https://graph.facebook.com/').get('me?' + urlencode({'access_token': token})) as res:
            fb_user = json.load(res)
    except ssl.SSLError:
        # TODO: Log this error? What to do when Facebook
        # connection has been compromised?
        return HttpResponseServerError()

    fb, created = FacebookCache.objects.get_or_create(uid=fb_user['id'])
    fb.name = fb_user['name']
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
        # First time login with Facebook
        try:
            profile = UserProfile.objects.get(pk=old_user_id)
            if not profile.user and not profile.facebook:
                profile.facebook = fb
            else:
                raise Exception()
        except:
            profile = UserProfile(id=gen_token(), facebook=fb)
    profile.save()

    request.session['user_id'] = profile.id

    # Just public user info
    user_info = json.dumps(get_user_info(profile, False))

    # Send this new user info to every channel where user is a player:
    for p in (1, 2):
        # Games where player p is this user
        query = Game.objects.filter(**{'p{}__user__exact'.format(p): profile})

        # Build the message to send to the game channels regarding player p
        msg = '\n'.join((str(p), user_info))

        # TODO: find a way to make this a single query, because I could not.
        for game in query:
            gevent.spawn(channel.post_update, game.channel(), 'p', msg)

    # Full user info
    user_info = json.dumps(get_user_info(profile, True))
    return HttpResponse(user_info, content_type='application/json')

@transaction.commit_on_success
def fb_logout(request):
    profile = UserProfile.get(request.session)
    if profile.user or profile.facebook:
        profile = UserProfile(id=gen_token())
        profile.save()
        request.session['user_id'] = profile.id

        user_info = json.dumps(get_user_info(profile, True))
        return HttpResponse(user_info, content_type='application/json')
    return HttpResponseForbidden()

def adhack(request, ad_id):
    ad_id = int(ad_id)
    return render_to_response('adhack.html',
        Context({'GOOGLE_AD_ID': settings.GOOGLE_AD_ID,
                 'GOOGLE_AD_SLOT': settings.GOOGLE_AD_SLOTS[ad_id]}),
        content_type='text/html; charset=utf-8')

def get_fb_request(request_id, conn, app_token):
    with conn.get('?'.join((request_id, app_token))) as res:
        return json.load(res)

def fb_notify_request(request, game_id):
    @transaction.commit_on_success
    def real_work(request_info, user_id, game_id):
        try:
            user = UserProfile.objects.get(pk=user_id)
            fb_profile = user.facebook
            if not fb_profile:
                return

            game = Game.objects.get(pk=game_id, p1__user__exact=user)
            if game.state != 0:
                return

            # The data received is untrusted, so we must quote it to avoid
            # allowng an attaker to forge Facebook requests from us.
            request_id = urlquote(request_info['request'], '')
            targets = [urlquote(t, '') for t in request_info['to']]
            cached = FacebookRequest(id=request_id, game=game, targets=targets)

            # Validate received information
            fb_request = fb_ograph_call(partial(get_fb_request, request_id))
            if fb_profile.uid != fb_request['from']['id'] or fb_request['data'] != game_id or game.p1.user != user:
                # Request is invalid, delete it from Facebook.
                start_cancel_request(cached)
            else:
                # Request passes validation test, save it.
                cached.save()
        except (ObjectDoesNotExist, KeyError):
            pass

    gevent.spawn(real_work, json.loads(request.body), request.session.get('user_id'), game_id)
    return HttpResponse()

# This function works on best effort, and returns no errors in case of invalid input.
def fb_cancel_request(request):
    class GiveUp(Exception):
        pass

    try:
        request_id = request.POST["request_id"]
        profile = UserProfile.get(request.session)
        if profile.facebook is None:
            raise GiveUp()
        uid = profile.facebook.uid

        fb_request = FacebookRequest.objects.get(pk=request_id)
        new_targets = [x for x in fb_request.targets if x != uid]
        if not new_targets:
            # Request cancellation on Facebook will be initiated automatically upon delete
            fb_request.delete()
        elif len(fb_request.targets) != len(new_targets):
            fb_request.targets = new_targets
            fb_request.save()

            start_cancel_request(FacebookRequest(id=request_id, targets=(uid,)))

    except (ObjectDoesNotExist, KeyError, GiveUp):
        pass
    except:
        raise

    return HttpResponseRedirect('/')

@transaction.commit_on_success
def fb_request_redirect(request):
    profile = UserProfile.get(request.session)
    user_id = getattr(profile.facebook, 'uid', None)
    request_ids = request.GET["request_ids"].split(',')

    must_authenticate = False
    found = False

    # This will try to validate each request id received, stopping at the first
    # valid one, and using it to build the user response.
    # TODO: handle multiple requests instead of just picking the first of them...
    for request_id in request_ids:
        request_id = urlquote(request_id, '')

        try:
            # First we check about this request on database
            fb_request = FacebookRequest.objects.get(pk=request_id)
            game = fb_request.game

            # If the game has already started, the request is invalid
            # (this should never happen, but just to be safe...)
            if game.state != 0:
                fb_request.delete()
                continue

            is_targeted = user_id in fb_request.targets

            # If this is a private game, we must ensure the user has
            # indeed received that request...
            if game.token:
                if user_id is None:
                    must_authenticate = True
                    continue
                if not is_targeted:
                    raise ObjectDoesNotExist()

            # Just for consistency, we ensure the stored request targets this user
            if user_id is not None and not is_targeted:
                fb_request.targets.append(user_id)
                fb_request.save()

        except ObjectDoesNotExist:
            # If don't know about this request on our database,
            # we query Facebook for updated intel.
            if user_id is None:
                full_reqid = request_id
            else:
                full_reqid = '_'.join((request_id, user_id))
            response = fb_ograph_call(partial(get_fb_request, full_reqid))
            try:
                game_id = response['data']
                game = Game.objects.get(pk=game_id)
                fb_user = game.p1.user.facebook
                if game.state != 1:
                    raise ObjectDoesNotExist()
                
                if game.token:
                    if fb_user is None or fb_user.uid != response['from']['id']:
                        raise ObjectDoesNotExist()
                    if user_id is None:
                        must_authenticate = True
                        continue

            except KeyError:
                # The request was completely invalid, just ignore it.
                continue
            except ObjectDoesNotExist:
                # The request is invalid, delete it from Facebook.
                start_cancel_request(FacebookRequest(id=request_id, targets=(user_id,)))
                continue

            fb_request, created = FacebookRequest.objects.get_or_create(id=request_id, defaults={'targets': [user_id]})
            if not created:
                fb_request.targets.append(user_id)

            fb_request.save()

        # The request is valid, break out to proceed to handle it:
        found = True
        break

    if found:
        return render_with_extra('accept_invite.html', profile, {'g': game, 'request_id': fb_request.id})
    if must_authenticate:
        pass # TODO: return a page asking user to authorize us with Facebook
    return render_with_extra('game404.html', profile, status=404) 

def index(request):
    if "request_ids" in request.GET:
        return fb_request_redirect(request)

    profile = UserProfile.get(request.session)
    playing_now = Game.objects.filter(Q(p1__user=profile) | Q(p2__user=profile)).exclude(state__gte=3)

    chosen = Game.objects.filter(state__exact=0, token__isnull=True).exclude(p1__user__exact=profile).order_by('?')[:5]
    new_games = []
    for game in chosen:
        info = {'id': game.id,
                'user': get_user_info(game.p1.user)
               }
        new_games.append(info)

    context = {'your_games': playing_now, 'new_games': new_games, 'like_url': settings.FB_LIKE_URL}
    return render_with_extra('index.html', profile, context)

@transaction.commit_on_success
def new_game(request):
    if request.method != 'POST':
        c = Context({'url': '/new_game/'})
        return render_to_response('post_redirect.html', c)

    profile = UserProfile.get(request.session)

    mine = [[0] * 16 for i in xrange(16)]

    indexes = list(itertools.product(xrange(16), repeat=2))
    gems = true_random.sample(indexes, 51)
    
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
    game.p1 = p1
    game.save()
    
    return HttpResponseRedirect('/game/' + str(game.id))

@transaction.commit_on_success
def join_game(request, game_id):
    profile = UserProfile.get(request.session)

    # If game is too old, render 404 game error screen
    try:
        game = Game.objects.get(pk=int(game_id))
    except ObjectDoesNotExist:
        return render_with_extra('game404.html', profile, status=404)

    # If already playing this game, redirect to game screen
    if game.what_player(profile):
        return HttpResponseRedirect('/game/' + str(game.id))

    # If user cannot start this game, then 403
    token = request.REQUEST.get('token')
    if game.state != 0 or (game.token and
                           token != game.token):
        return render_with_extra('game403.html', profile, status=403)

    # If we got here via GET, return a page that will make the client/user
    # retry via POST. Done so that Facebook and other robots do not join
    # the game in place of a real user.
    if request.method != 'POST':
        url = '/game/{}/join/'.format(game_id)
        if token:
            url = '{}?token={}'.format(url, token)
        c = Context({'url': url})
        return render_to_response('post_redirect.html', c)

    p2 = Player(user=profile)
    p2.save()

    game.p2 = p2
    game.state = 1
    game.save()

    # Ivalidate all facebook requests on this game...
    game.facebookrequest_set.all().delete()

    transaction.commit()

    ch_id = game.channel()
    
    # Game state change
    channel.post_update(ch_id, 'g', str(game.state), game.seq_num)

    # Player info display
    outdata = '2\n' + json.dumps(get_user_info(profile))
    channel.post_update(ch_id, 'p', outdata)

    return HttpResponseRedirect('/game/' + game_id)

@transaction.commit_on_success
def abort_game(request, game_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    game = get_object_or_404(Game, pk=game_id)
    if game.state == 0:
        profile = UserProfile.get(request.session)
        pdata = game.what_player(profile)
        if pdata:
            pdata[1].delete()
            game.delete()
            return HttpResponseRedirect('/')

    return HttpResponseForbidden()    

@transaction.commit_on_success
def claim_game(request, game_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    game = get_object_or_404(Game, pk=game_id)
    if game.state not in (1,2):
        return HttpResponseForbidden()
    
    profile = UserProfile.get(request.session)
    pdata = game.what_player(profile)
    if pdata:
        my_number, me = pdata
    else:
        return HttpResponseForbidden()

    term = request.POST.get('terminate') 
    if term != 'z' and (my_number == game.state or game.timeout_diff() > 0):
        return HttpResponseForbidden()
    
    if term == 'y':
        points = game.mine.count(tile_encode(19)) + game.mine.count(tile_encode(20))
        profile.total_score += points
        profile.save()
        game.state = my_number + 4 

    # If one of the players give up...
    #TODO: You better fix this, lowlife fucking piece of , z? before was 
    #Yes or No, now that YOU added a state, YOU FIX IT!!!
    elif term == 'z':
        for pnum,player in ((1,game.p1),(2,game.p2)):
            points = game.mine.count(tile_encode(pnum + 18))
            prof = player.user
            prof.total_score += points
            prof.games_finished += 1
            if pnum != my_number:
                prof.games_won += 1
                game.state = pnum + 4
            prof.save()
    else:
        game.state = my_number;

    game.save()
    transaction.commit()

    channel.post_update(game.channel(), 'g', str(game.state), game.seq_num)
    
    if term == 'y':
        gevent.spawn(publish_score, me.user)
    elif term == 'z':
        gevent.spawn(publish_score, game.p1.user)
        gevent.spawn(publish_score, game.p2.user)

    return HttpResponse()

@transaction.commit_on_success
def game(request, game_id):
    # TODO: maybe control who can watch a game
    profile = UserProfile.get(request.session)
    #game = get_object_or_404(Game, pk=game_id)
    try:
        game = Game.objects.get(pk=int(game_id))
    except ObjectDoesNotExist:
        return render_with_extra('game404.html', profile, status=404)

    user_id = profile.display_name()

    p1_info = get_user_info(game.p1.user)
    data = {'state': game.state,
            'game_id': game_id,
            'seq_num': game.seq_num,
            'channel': game.channel,
            'p1_last_move': game.p1.last_move,
            'player_info': {1: p1_info,
                            2: None},
           }

    if(game.p2):
        p2_info = get_user_info(game.p2.user)
        data['p2_last_move'] = game.p2.last_move
        data['player_info'][2] = p2_info
        #if (game.state <= 2):
        data['time_left'] = max(0, game.timeout_diff())

    # Does not display chat if both users are logged on facebook
    try:
        display_chat = (p1_info.auth.fb and p2_info.auth.fb)
    except AttributeError:
        display_chat = False

    pdata = game.what_player(profile)
    if pdata:
        my_number, me = pdata
        data['tnt_used'] = not me.has_tnt
        data['player'] = my_number
        me.save()

        if game.state == 0:
            protocol = 'https' if request.is_secure() else 'http'
            data['base_url'] = '{}://{}'.format(protocol, request.get_host())

    if game.state == 0 and game.token: # Uninitialized private game
        data['token'] = game.token
    else:
        masked = mine_mask(game.mine, game.state in (3, 4))
        if masked.count('?') != 256:
            data['mine'] = masked

    return render_with_extra('game.html', profile, data)


@transaction.commit_on_success
def rematch(request, game_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    game = get_object_or_404(Game, pk=game_id)
    if game.state <= 2:
        return HttpResponseForbidden()
    #if datetime.datetime.now() - game.last_move_time >= 45:
        #return HttpResponseForbidden()
    pdata = game.what_player(UserProfile.get(request.session))
    if not pdata:
        return HttpResponseForbidden()
    
    obj, created = Rematch.objects.get_or_create(game=game)
    me, player = pdata
    if me == 1:
        obj.p1_click = True
    elif me == 2:
        obj.p2_click = True

    obj.save()

    ready_state = {'p1_click':obj.p1_click, 'p2_click':obj.p2_click}
    if obj.p1_click and obj.p2_click:
        cg = Game.create()
        p = Player(user=game.p2.user)
        p.save()
        cg.p1 = p
        p = Player(user=game.p1.user)
        p.save()
        cg.p2 = p
        cg.state = 1
        cg.save()
        ready_state['game_id'] = cg.id

    channel.post_update(game.channel(), 'r', json.dumps(ready_state))
    
    return HttpResponse()

@transaction.commit_on_success
def move(request, game_id):
    if request.method != 'POST':
        return HttpResponseForbidden()

    game = get_object_or_404(Game, pk=game_id)

    pdata = game.what_player(UserProfile.get(request.session))
    if not pdata or pdata[0] != game.state:
        return HttpResponseForbidden()

    player, me = pdata

    try:
        m = int(request.REQUEST['m'])
        n = int(request.REQUEST['n'])
        if not (0 <= m <= 15 and 0 <= n <= 15):
            raise ValueError
    except:
        return HttpResponseBadRequest()

    mine = mine_decode(game.mine)

    to_reveal = [(m, n)]
    tnt_used = False

    if request.REQUEST.get('tnt') == 'y':
        if not me.has_tnt:
            return HttpResponseBadRequest()
        me.has_tnt = False
        to_reveal = itertools.product(xrange(max(m-2, 0),
                                             min(m+3, 16)),
                                      xrange(max(n-2, 0),
                                             min(n+3, 16)))
        tnt_used = True

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

    if mine[m][n] <= 18 or tnt_used:
        game.state = (game.state % 2) + 1

    new_mine = mine_encode(mine)
    points = [new_mine.count(tile_encode(19)), new_mine.count(tile_encode(20))]

    if points[0] >= 26 or points[1] >= 26:
        game.state = player + 2

    coded_move = '%s%x%x' % ('b' if tnt_used else 'd', m, n)
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

    result = itertools.chain((str(game.state), str(player), coded_move), ['%d,%d:%c' % x for x in revealed])
    result = '\n'.join(result)

    # Everything is OK until now, so commit DB transaction
    transaction.commit()

    # Post the update to the users...
    channel.post_update(game.channel(), 'g', result, game.seq_num)

    # ... and then publish the scores on FB, if game is over.
    if game.state >= 3: 
        gevent.spawn(publish_score, game.p1.user)
        gevent.spawn(publish_score, game.p2.user)
    return HttpResponse()

def donate(request):
    profile = UserProfile.get(request.session)
    return render_with_extra('donate.html', profile, {'like_url': settings.FB_LIKE_URL})

def info(request, page):
    if page not in info.existing_pages:
        raise Http404
    for locale in (request.LANGUAGE_CODE, 'en'):
        try:
            return render_with_extra('{}/{}.html'.format(locale, page), UserProfile.get(request.session))
        except TemplateDoesNotExist:
            continue
info.existing_pages = frozenset(('about', 'howtoplay', 'sourcecode', 'contact', 'privacy', 'terms'))

