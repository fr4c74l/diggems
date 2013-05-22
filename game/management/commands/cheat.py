from django.core.management.base import BaseCommand, CommandError
from game.models import *
from game.game_helpers import mine_decode

class Command(BaseCommand):
    help = 'Show the gems location of a game'

    def handle(self, *args, **options):
        game_id = int(args[0])
        g = Game.objects.get(id=game_id)
        mine = mine_decode(g.mine)
        for m in xrange(16):
            for n in xrange(16):
                print ('x' if mine[n][m] in (9, 19, 20) else 'o'),
            print '\n',
