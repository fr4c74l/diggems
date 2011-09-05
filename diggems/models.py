from django.db import models

class Game(models.Model):
    mine = models.CharField(max_length=256)
    state = models.SmallIntegerField(default=0)
    token = models.CharField(max_length=22)
    p1_channel = models.CharField(max_length=22, blank=True, null=True)
    p2_channel = models.CharField(max_length=22, blank=True, null=True)
