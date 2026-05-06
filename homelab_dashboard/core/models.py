from django.db import models

class Service(models.Model):
    name = models.CharField(max_length=60)
    address = models.CharField(max_length=40)
    port = models.PositiveIntegerField()
    url_name = models.CharField(max_length=150, blank=True)
    is_online = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
class MediaPanel(models.Model):
    name = models.CharField(max_length=60)
    url_name = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name