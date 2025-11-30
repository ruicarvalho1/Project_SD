from django.db import models
import time

class Peer(models.Model):
    peer_id=models.CharField(max_length=200,unique=True)
    host=models.CharField(max_length=200)
    port=models.IntegerField()
    last_seen=models.FloatField(default=time.time)

    def __str__(self):
        return f"{self.peer_id} @ {self.host}:{self.port}"

