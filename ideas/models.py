import uuid
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class AwardRound(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=180)
    description = models.TextField()
    award = models.CharField(max_length=180, default="BIC Community Choice Award")
    submissions_open_at = models.DateTimeField(default=timezone.now)
    voting_starts_at = models.DateTimeField()
    voting_ends_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submissions_open_at"]
        constraints = [
            models.CheckConstraint(condition=models.Q(voting_starts_at__gt=models.F("submissions_open_at")), name="round_submission_window"),
            models.CheckConstraint(condition=models.Q(voting_ends_at__gt=models.F("voting_starts_at")), name="round_voting_window"),
        ]

    def clean(self):
        if self.submissions_open_at and self.voting_starts_at and self.voting_starts_at <= self.submissions_open_at:
            raise ValidationError({"voting_starts_at": "Voting must start after submissions open."})
        if self.voting_starts_at and self.voting_ends_at and self.voting_ends_at <= self.voting_starts_at:
            raise ValidationError({"voting_ends_at": "Voting must end after it starts."})

    @property
    def status(self):
        now = timezone.now()
        if now < self.submissions_open_at:
            return "upcoming"
        if now < self.voting_starts_at:
            return "submissions"
        if now < self.voting_ends_at:
            return "voting"
        return "closed"

    @property
    def status_label(self):
        return {"upcoming": "Coming soon", "submissions": "Submissions open", "voting": "Voting open", "closed": "Results are in"}[self.status]

    def __str__(self):
        return self.title


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
    award_round = models.ForeignKey(AwardRound, on_delete=models.PROTECT, null=True, blank=True, related_name="entries")
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


class Ballot(models.Model):
    award_round = models.ForeignKey(AwardRound, on_delete=models.PROTECT, related_name="ballots")
    idea = models.ForeignKey(Idea, on_delete=models.PROTECT, related_name="ballots")
    voter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="award_ballots")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["award_round", "voter"], name="one_ballot_per_member_per_round")]

    def clean(self):
        if self.idea_id and self.award_round_id and self.idea.award_round_id != self.award_round_id:
            raise ValidationError("This idea does not belong to the selected award round.")

