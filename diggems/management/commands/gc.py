from django.core.management.base import BaseCommand, CommandError
from diggems.models import *
import datetime

class Command(BaseCommand):
    help = 'Cleanup the old games and unseen guest users.'

    def handle(self, *args, **options):
        hour_ago = datetime.datetime.now() - datetime.timedelta(hours=1)
        q = Player.objects.exclude(last_seen__gte=hour_ago)
        q = q.exclude(game_as_p1__p2__last_seen__gte=hour_ago)
        q = q.exclude(game_as_p2__p1__last_seen__gte=hour_ago)
        q.delete()

        week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        q = UserProfile.objects.filter(user__isnull=True,
                                       facebook_id__isnull=True,
                                       last_seen__lt=week_ago)
        q.delete()
