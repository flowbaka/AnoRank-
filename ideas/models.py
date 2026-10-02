import uuid 

from django.conf import settings
from django.db import models

class Idea(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="submitted_ideas",

    )

    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.title

