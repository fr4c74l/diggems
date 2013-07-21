# Copyright 2011 Lucas Clemente Vella
# Software under Affero GPL license, see LICENSE.txt

import game_helpers
import datetime
from django.db import models
from django.db.models import F
from django.db.models.signals import pre_delete
from django.contrib.auth.models import User

class FacebookCache(models.Model):
    uid = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)
    
    def pub_info(self):
        return {'uid': self.uid,
                'name': self.name}

class UserProfile(models.Model):
    id = models.CharField(max_length=22, primary_key=True)
    user = models.OneToOneField(User, blank=True, null=True, unique=True)
    facebook = models.OneToOneField(FacebookCache, blank=True,
                                    null=True, unique=True)
    games_finished = models.IntegerField(default=0)
    games_won = models.IntegerField(default=0)
    total_score = models.IntegerField(default=0)
    last_seen = models.DateTimeField(auto_now=True, db_index=True)

    def merge(self, other):
        # Update players user to the unified one
        Player.objects.filter(user=other).update(user=self)

        # Can't allow someone to play against itself, delete those games
        Game.objects.filter(p1__user__exact=F('p2__user')).delete()
        
        # Update scores
        self.games_finished += other.games_finished
        self.games_won += other.games_won
        self.total_score += other.total_score
        self.save()

        # No longer needed
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
                prof.id = game_helpers.gen_token()
                request.session['user_id'] = prof.id
        else:
            # Authenticated by us
            prof = request.user.get_profile()

            # Authenticated user should not have user_id
            if user_id:
                del request.session['user_id']

        # Must always save, to update timestamp
        prof.save()
        return prof

class Player(models.Model):
    has_tnt = models.BooleanField(default=True)
    last_seen = models.DateTimeField(auto_now=True)
    last_move = models.CharField(max_length=3, blank=True, null=True)
    user = models.ForeignKey(UserProfile)

class Game(models.Model):
    mine = models.CharField(max_length=256)
    state = models.SmallIntegerField(default=0, db_index=True)
    seq_num = models.IntegerField(default=0)
    token = models.CharField(max_length=22, blank=True, null=True)
    channel = models.CharField(max_length=22, unique=True)
    p1 = models.OneToOneField(Player, related_name='game_as_p1')
    p2 = models.OneToOneField(Player, blank=True, null=True, related_name='game_as_p2')
    last_move_time = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        self.seq_num = self.seq_num + 1
        super(Game, self).save(*args, **kwargs)

    def what_player(self, user):
        if self.p1 and self.p1.user == user:
            return (1, self.p1)
        elif self.p2 and self.p2.user == user:
            return (2, self.p2)
        else:
            return None
            
    def timeout_diff(self):
        return 45 - (datetime.datetime.now() - self.last_move_time).seconds

def delete_game_channel(sender, **kwargs):
    game_helpers.delete_channel(kwargs['instance'].channel)

pre_delete.connect(delete_game_channel, sender=Game)
