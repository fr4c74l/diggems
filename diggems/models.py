from django.db import models

class Player(models.Model):
    channel = models.CharField(max_length=22, unique=True)
    has_bomb = models.BooleanField(default=True)
    last_seen = models.DateTimeField(auto_now=True)

class Game(models.Model):
    mine = models.CharField(max_length=256)
    state = models.SmallIntegerField(default=0)
    token = models.CharField(max_length=22)
    p1 = models.OneToOneField(Player, blank=True, null=True, related_name='game_as_p1')
    p2 = models.OneToOneField(Player, blank=True, null=True, related_name='game_as_p2')
