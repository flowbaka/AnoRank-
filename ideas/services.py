from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count

from .models import AwardRound, Ballot, Idea


def can_vote(user):
    return user.is_authenticated and user.is_active


def cast_ballot(user, round_id, idea_id):
    """Recheck the deadline while the round is locked."""
    with transaction.atomic():
        award_round = AwardRound.objects.select_for_update().get(pk=round_id)
        if not can_vote(user):
            raise PermissionDenied("Sign in to vote.")
        if award_round.status != "voting":
            raise ValidationError("Voting is not open for this round.")
        idea = Idea.objects.filter(pk=idea_id, award_round=award_round).first()
        if not idea:
            raise ValidationError("Choose an idea from this award round.")
        ballot, created = Ballot.objects.update_or_create(award_round=award_round, voter=user, defaults={"idea": idea})
        return ballot, created


def standings(award_round):
    entries = list(award_round.entries.annotate(vote_count=Count("ballots")).order_by("-vote_count", "created_at", "pk"))
    highest = entries[0].vote_count if entries else 0
    winners = [entry for entry in entries if highest > 0 and entry.vote_count == highest] if award_round.status == "closed" else []
    return entries, winners
