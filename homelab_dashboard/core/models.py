from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Service(models.Model):

    name = models.CharField(max_length=60)

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    address = models.CharField(max_length=40)
    port = models.PositiveIntegerField()

    url_name = models.CharField(
        max_length=150,
        blank=True
    )

    is_online = models.BooleanField(default=False)

    status_checked_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.name


class ServiceStatus(models.Model):

    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="history"
    )

    is_online = models.BooleanField()

    checked_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-checked_at"]


class SystemMetric(models.Model):

    cpu_percent = models.FloatField()
    ram_percent = models.FloatField()
    disk_percent = models.FloatField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )


class MediaPanel(models.Model):

    name = models.CharField(max_length=60)
    url_name = models.CharField(max_length=150)

    created_at = models.DateTimeField(
        auto_now_add=True
    )