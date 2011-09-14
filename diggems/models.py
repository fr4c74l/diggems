from django.db import models
from django.contrib.auth.models import User
from game_helpers import delete_channel

class UserProfile(models.Model):
    user = models.OneToOneField(User, blank=True, null=True, unique=True)
    facebook_id = models.IntegerField(blank=True, null=True, unique=True)
    last_seen = models.DateTimeField(auto_now=True)
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
                request.session['user_id'] = prof.id
        else:
            # Authenticated by us
            prof = request.user.userprofile
            # Now we check for unusual situations
            if not prof:
                # Probably a new user: is authenticated, but have no
                # related UserProfile. Create one for him.
                prof = UserProfile(user=request.user)
            if user_id:
                # Just authenticated, has an old UserProfile to be merged
                try:
                    old_prof = UserProfile.objects.get(id=user_id)
                except UserProfile.DoesNotExist:
                    del request.session['user_id']

        prof.save()
        return prof

class Player(models.Model):
    channel = models.CharField(max_length=22, unique=True)
    has_bomb = models.BooleanField(default=True)
    last_seen = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(UserProfile)
    def delete(self, *args, **kwargs):
        delete_channel(self.channel)
        super(Player, self).delete(*args, **kwargs)

class Game(models.Model):
    private = models.BooleanField()
    mine = models.CharField(max_length=256)
    state = models.SmallIntegerField(default=0)
    token = models.CharField(max_length=22, unique=True)
    p1 = models.OneToOneField(Player, blank=True, null=True, related_name='game_as_p1')
    p2 = models.OneToOneField(Player, blank=True, null=True, related_name='game_as_p2')
    def what_player(self, user):
        if self.p1.user == user:
            return 1
        elif self.p2.user == user:
            return 2
        else:
            return None
