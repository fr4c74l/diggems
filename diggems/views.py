import itertools
import radix64
import random
from models import *
from django.shortcuts import get_object_or_404, render_to_response
from django.http import *

def mine_encode(mine):
    mine = itertools.chain.from_iterable(mine)
    mine = map(lambda n: chr(n+10), mine)
    return ''.join(mine)

def mine_decode(mine):
    pass #TODO: To be continued, too...

def mine_mask(mine):
    def tile_mask(tile):
        n = ord(tile)-10
        if n < 10:
            return '?'
        elif n < 19:
            return str(n - 10)
        elif n == 19:
            return 'r'
        else:
            return 'b'

    return ''.join(map(tile_mask, mine))

def gen_token():
    return radix64.encode(random.getrandbits(132))

# Stubs:
def create_channel():
    return gen_token()

def delete_channel(channel):
    pass

def post_update(channel, msg):
    pass
# End of stubs

def game_must_exist(func):
    def exist_check(request, game_id):
        try:
            game = Game.object.get(pk=game_id)
        except DoesNotExist:
            return HttpResponseNotFound()
        func(request, game)

    return exist_check

def new_game(request):
    mine = [[0] * 16 for i in xrange(16)]

    indexes = list(itertools.product(xrange(16), repeat=2))
    gems = random.sample(indexes, 51)

    for (m, n) in gems:
        mine[m][n] = 9

    for m, n in indexes:
        if mine[m][n] == 0:
            surroundings = ((-1,-1),(-1, 0),(-1, 1),
                            ( 0,-1),        ( 0, 1),
                            ( 1,-1),( 1, 0),( 1, 1))

            for (dx, dy) in surroundings:
                x = m + dx
                y = n + dy
                if 0 <= x <= 15 and 0 <= y <= 15 and mine[x][y] == 9:
                    mine[m][n] += 1

    game = Game()
    game.mine = mine_encode(mine)
    game.token = gen_token()
    game.p1_channel = create_channel()
    game.save()

    request.session[game.id] = '1'

    return HttpResponseRedirect('game/' + str(game.id))

@game_must_exist
def join_game(request, game):
    if game.state != 0 or request.GET['token'] != game.token:
        return HttpResponseForbidden()

    request.session[game.id] = '2'
    game.p2_channel = create_channel()
    game.state = 1
    game.save()

    return HttpResponseRedirect('game/' + str(game.id))

@game_must_exist
def game(request, game):
    data = {'state', game.state}

    player = request.session.get(game.id, '0')
    if player == '1':
        data['channel'] = game.p1_channel
    elif player == '2':
        data['channel'] = game.p2_channel
    else:
        return HttpResponseForbidden()

    if game.state == 0: # Uninitialized game
        data['token'] = game.token
    else:
        data['fullstate'] = mine_mask(game.mine)

    return render_to_response('game.html', data)

@game_must_exist
def move(request, game):
    if ((not 1 <= game.state <= 2)
        or str(game.state) != request.session.get(game.id, '0')):
        return HttpResponseForbidden()

    try:
        m = int(request.GET['m'])
        n = int(request.GET['n'])
        if not (0 <= m <= 15 and 0 <= n <= 15):
            raise ValueError
    except ValueError:
        return HttpResponseBadRequest()

    mine = mine_decode(game.mine)
    # TODO: To be continued...
