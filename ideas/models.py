import uuid
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

class Idea(models.Model):
    class Category(models.TextChoices):
        COMMUNITY = "community", "Community"
        TECHNOLOGY = "technology", "Technology"
        ENVIRONMENT = "environment", "Environment"
        EDUCATION = "education", "Education"
        EVERYDAY = "everyday", "Everyday life"

    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.COMMUNITY)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="submitted_ideas",

    )

    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-created_at"]
    def __str__(self):
        return self.title


class Rating(models.Model):
    idea = models.ForeignKey(Idea, on_delete=models.CASCADE, related_name="ratings")
    voter_id = models.UUIDField()
    feasibility = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    impact = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    originality = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["idea", "voter_id"], name="one_rating_per_browser"),
            models.CheckConstraint(condition=models.Q(feasibility__gte=1, feasibility__lte=5), name="valid_feasibility"),
            models.CheckConstraint(condition=models.Q(impact__gte=1, impact__lte=5), name="valid_impact"),
            models.CheckConstraint(condition=models.Q(originality__gte=1, originality__lte=5), name="valid_originality"),
        ]

