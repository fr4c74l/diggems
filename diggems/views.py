import itertools
import datetime
from game_helpers import *
from models import *
from django.shortcuts import get_object_or_404, render_to_response
from django.http import *

def new_game(request):
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

    p1 = Player()
    p1.channel = create_channel()
    p1.last_seen = datetime.datetime.now()
    p1.save()

    game = Game()
    game.mine = mine_encode(mine)
    game.token = gen_token()
    game.p1 = p1
    game.save()

    request.session[game.id] = '1'

    return HttpResponseRedirect('/game/' + str(game.id))

def join_game(request, game_id):
    game = get_object_or_404(Game, pk=game_id)

    if request.session.get(game.id, '0') in ('1', '2'):
        return HttpResponseRedirect('/game/' + str(game.id))

    if game.state != 0 or request.GET['token'] != game.token:
        return HttpResponseForbidden()

    request.session[game.id] = '2'
    p2 = Player()
    p2.channel = create_channel()
    p2.last_seen = datetime.datetime.now()
    p2.save()

    game.p2 = p2
    game.state = 1
    game.save()

    post_update(game.p1.channel, str(game.state))
    return HttpResponseRedirect('/game/' + game_id)

def game(request, game_id):
    game = get_object_or_404(Game, pk=game_id)

    data = {'state': game.state,
            'game_id': game_id}

    player = request.session.get(game.id, '0')
    if player == '1':
        me = game.p1
    elif player == '2':
        me = game.p2
    else:
        return HttpResponseForbidden()

    data['bomb_used'] = not me.has_bomb
    data['channel'] = me.channel
    data['player'] = player

    if game.state == 0: # Uninitialized game
        data['token'] = game.token
    else:
        masked = mine_mask_encoded(game.mine)
        if masked.count('?') != 256:
            data['mine'] = masked

    return render_to_response('game.html', data)

def move(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    player = request.session.get(game.id, '0')

    if (not 1 <= game.state <= 2) or str(game.state) != player:
        return HttpResponseForbidden()

    if player == '1':
        me = game.p1
        other = game.p2
    else:
        me = game.p2
        other = game.p1

    try:
        m = int(request.GET['m'])
        n = int(request.GET['n'])
        if not (0 <= m <= 15 and 0 <= n <= 15):
            raise ValueError
    except:
        return HttpResponseBadRequest()

    mine = mine_decode(game.mine)

    if request.GET.get('bomb', 'n') == 'y':
        if not me.has_bomb:
            return HttpResponseBadRequest()
        me.has_bomb = False
        me.save()
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
        if mine[m][n] == 19 and player == '2':
            mine[m][n] = 20
        revealed.append((m, n, tile_mask(mine[m][n])))
        if old == 0:
            for_each_surrounding(m, n, reveal)

    for m, n in to_reveal:
        reveal(m, n)

    if revealed and revealed[0]:
        m, n, s = revealed[0]
        if mine[m][n] <= 18 or bomb_used:
            game.state = (game.state % 2) + 1

    new_mine = mine_encode(mine)
    point_p1 = new_mine.count(tile_encode(19))
    point_p2 = new_mine.count(tile_encode(20))

    if point_p1 >= 26 or point_p2 >= 26:
        game.state = int(player) + 2

    game.mine = new_mine
    game.save()

    result = str(game.state) + '\n' + '\n'.join(map(lambda x: '%d,%d:%c' % x, revealed))

    post_update(other.channel, result)
    if game.state >= 3:
        delete_channel(game.p1.channel)
        delete_channel(game.p2.channel)
        
    return HttpResponse(result, mimetype='text/plain')
