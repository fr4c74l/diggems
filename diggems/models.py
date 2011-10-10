# Copyright 2011 Lucas Clemente Vella
# Software under Affero GPL license, see LICENSE.txt

from django.db import models
from django.db.models import F
from django.db.models.signals import pre_delete
from django.contrib.auth.models import User
from game_helpers import delete_channel, gen_token

class FacebookCache(models.Model):
    uid = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)
    access_token = models.CharField(max_length=500)
    expires = models.DateTimeField()

class UserProfile(models.Model):
    id = models.CharField(max_length=22, primary_key=True)
    user = models.OneToOneField(User, blank=True, null=True, unique=True)
    facebook = models.OneToOneField(FacebookCache, blank=True,
                                       null=True, unique=True)
    last_seen = models.DateTimeField(auto_now=True, db_index=True)

    def merge(self, other):
        Player.objects.filter(user=other).update(user=self)
        # Can't allow someone to play against itself
        Game.objects.filter(p1__user__exact=F('p2__user')).delete()
        other.delete()

    @staticmethod
    def get(request):
        is_auth = request.user.is_authenticated()
        user_id = request.session.get('user_id')

        if not is_auth:
            # Not authenticated by us
            if user_id:
                # Recurring FB or guest user
                try:
                    prof = UserProfile.objects.get(id=user_id)
                except UserProfile.DoesNotExist:
                    # Old cookie, invalidate the id
                    user_id = None
                
            if not user_id:
                # New guest user, create a temporary guest profile
                prof = UserProfile()
                prof.id = gen_token()
                request.session['user_id'] = prof.id
        else:
            # Authenticated by us
            prof = request.user.get_profile()

            # Authenticated user should not have user_id
            if user_id:
                del request.session['user_id']

        prof.save()
        return prof

class Player(models.Model):
    channel = models.CharField(max_length=22, unique=True)
    has_bomb = models.BooleanField(default=True)
    last_seen = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(UserProfile)

def delete_player_channel(sender, **kwargs):
    delete_channel(kwargs['instance'].channel)

pre_delete.connect(delete_player_channel, sender=Player)

class Game(models.Model):
    private = models.BooleanField()
    mine = models.CharField(max_length=256)
    state = models.SmallIntegerField(default=0, db_index=True)
    seq_num = models.IntegerField(default=0)
    token = models.CharField(max_length=22, unique=True)
    p1 = models.OneToOneField(Player, blank=True, null=True, related_name='game_as_p1')
    p2 = models.OneToOneField(Player, blank=True, null=True, related_name='game_as_p2')

    def save(self, *args, **kwargs):
        self.seq_num = self.seq_num + 1
        super(Game, self).save(*args, **kwargs)

    def what_player(self, user):
        if self.p1 and self.p1.user == user:
            return (1, self.p1, self.p2)
        elif self.p2 and self.p2.user == user:
            return (2, self.p2, self.p1)
        else:
            return None
