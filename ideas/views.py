import uuid

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Avg, Count, ExpressionWrapper, F, FloatField, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import CommunitySignupForm, IdeaForm, RatingForm
from .models import AwardRound, Ballot, Idea, Rating
from .services import can_vote, cast_ballot, standings


def scored_ideas():
    return Idea.objects.annotate(
        feasibility_avg=Avg("ratings__feasibility"),
        impact_avg=Avg("ratings__impact"),
        originality_avg=Avg("ratings__originality"),
        rating_count=Count("ratings"),
    ).annotate(score=ExpressionWrapper(
        (F("feasibility_avg") + F("impact_avg") + F("originality_avg")) / 3.0,
        output_field=FloatField(),
    ))


def home(request, mode="discover"):
    query = request.GET.get("q", "").strip()[:200]
    category = request.GET.get("category", "")
    sort = request.GET.get("sort", "top" if mode == "leaderboard" else "newest")
    if sort not in ("newest", "top", "discussed"):
        sort = "newest"
    saved_ids = request.session.get("saved_ideas", [])
    ideas = scored_ideas()
    if mode == "saved":
        ideas = ideas.filter(public_id__in=saved_ids)
    elif mode == "leaderboard":
        ideas = ideas.filter(rating_count__gt=0)
    if query:
        ideas = ideas.filter(Q(title__icontains=query) | Q(description__icontains=query))
    if category in Idea.Category.values:
        ideas = ideas.filter(category=category)
    else:
        category = ""
    if sort == "top":
        ideas = ideas.order_by(F("score").desc(nulls_last=True), "-rating_count", "-created_at")
    elif sort == "discussed":
        ideas = ideas.order_by("-rating_count", "-created_at")
    else:
        ideas = ideas.order_by("-created_at")
    page = Paginator(ideas, 9).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "ideas/home.html", {
        "page_obj": page, "mode": mode, "q": query, "category": category,
        "sort": sort, "categories": Idea.Category.choices, "saved_ids": saved_ids,
        "querystring": params.urlencode(), "total_ideas": Idea.objects.count(),
        "total_ratings": Rating.objects.count(),
        "latest_round": AwardRound.objects.first(),
    })


def submit_idea(request, round_id=None):
    award_round = get_object_or_404(AwardRound, public_id=round_id) if round_id else None
    if award_round:
        if not can_vote(request.user):
            return redirect_to_login(request.get_full_path())
        if award_round.status != "submissions":
            messages.error(request, "Submissions are not open for this award round.")
            return redirect("award_detail", round_id=award_round.public_id)
    form = IdeaForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            if award_round:
                award_round = AwardRound.objects.select_for_update().get(pk=award_round.pk)
                if award_round.status != "submissions":
                    messages.error(request, "The submission deadline has passed.")
                    return redirect("award_detail", round_id=award_round.public_id)
            idea = form.save(commit=False)
            idea.creator = request.user if award_round else None
            idea.award_round = award_round
            idea.save()
        messages.success(request, "Your idea is live. Let the idea speak for itself.")
        return redirect("idea_detail", public_id=idea.public_id)
    return render(request, "ideas/submit.html", {"form": form, "mode": "awards" if award_round else "submit", "award_round": award_round})


def idea_detail(request, public_id):
    idea = get_object_or_404(scored_ideas(), public_id=public_id)
    rating = None
    voter_id = request.session.get("voter_id")
    if voter_id:
        rating = Rating.objects.filter(idea=idea, voter_id=voter_id).first()
    form = RatingForm(instance=rating)
    if request.method == "POST":
        form = RatingForm(request.POST, instance=rating)
        if form.is_valid():
            if not voter_id:
                voter_id = str(uuid.uuid4())
                request.session["voter_id"] = voter_id
            Rating.objects.update_or_create(idea=idea, voter_id=voter_id, defaults=form.cleaned_data)
            messages.success(request, "Your rating has been updated." if rating else "Thanks. Your rating is part of the bigger picture.")
            return redirect("idea_detail", public_id=idea.public_id)
    criteria = [
        ("Feasibility", "Could this realistically work?", idea.feasibility_avg),
        ("Impact", "How much positive change could it make?", idea.impact_avg),
        ("Originality", "Does it bring a fresh approach?", idea.originality_avg),
    ]
    return render(request, "ideas/detail.html", {
        "idea": idea, "form": form, "existing_rating": rating, "criteria": criteria,
        "is_saved": str(idea.public_id) in request.session.get("saved_ideas", []),
        "related_ideas": scored_ideas().filter(category=idea.category).exclude(pk=idea.pk)[:3],
        "award_votes": idea.ballots.count() if idea.award_round_id else 0,
        "your_ballot": Ballot.objects.filter(award_round_id=idea.award_round_id, voter=request.user).first() if idea.award_round_id and request.user.is_authenticated else None,
    })


@require_POST
def toggle_save(request, public_id):
    idea = get_object_or_404(Idea, public_id=public_id)
    saved = request.session.get("saved_ideas", [])
    idea_id = str(idea.public_id)
    if idea_id in saved:
        saved.remove(idea_id)
        messages.success(request, "Idea removed from your saved list.")
    elif len(saved) < 200:
        saved.append(idea_id)
        messages.success(request, "Idea saved for later.")
    else:
        messages.error(request, "Your saved list is full. Remove an idea before adding another.")
    request.session["saved_ideas"] = saved
    url = reverse("saved") if request.POST.get("return_to") == "saved" else reverse("idea_detail", kwargs={"public_id": public_id})
    return HttpResponseRedirect(url)


def about(request):
    return render(request, "ideas/about.html", {"mode": "about"})


def award_list(request):
    rounds = AwardRound.objects.annotate(entry_count=Count("entries", distinct=True), ballot_count=Count("ballots", distinct=True))
    return render(request, "ideas/awards.html", {"rounds": rounds, "mode": "awards"})


def award_detail(request, round_id):
    award_round = get_object_or_404(AwardRound, public_id=round_id)
    entries, winners = standings(award_round)
    previous_count, rank = None, 0
    for position, entry in enumerate(entries, start=1):
        if entry.vote_count != previous_count:
            rank = position
        entry.rank = rank
        previous_count = entry.vote_count
    ballot = Ballot.objects.filter(award_round=award_round, voter=request.user).select_related("idea").first() if request.user.is_authenticated else None
    return render(request, "ideas/award_detail.html", {
        "award_round": award_round, "entries": entries, "winners": winners,
        "total_votes": sum(entry.vote_count for entry in entries), "your_ballot": ballot, "mode": "awards",
    })


@login_required
@require_POST
def vote(request, round_id, public_id):
    award_round = get_object_or_404(AwardRound, public_id=round_id)
    idea = get_object_or_404(Idea, public_id=public_id, award_round=award_round)
    try:
        ballot, created = cast_ballot(request.user, award_round.pk, idea.pk)
    except ValidationError as error:
        messages.error(request, error.messages[0])
    else:
        messages.success(request, "Your vote is counted." if created else "Your vote has been updated. Only your latest choice counts.")
    return redirect("award_detail", round_id=award_round.public_id)


def signup(request):
    if request.user.is_authenticated:
        return redirect("account")
    form = CommunitySignupForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = form.save()
        login(request, user)
        messages.success(request, "Welcome to AnoRank. You can now enter award rounds and vote.")
        return redirect("awards")
    return render(request, "ideas/signup.html", {"form": form})


@login_required
def account(request):
    return render(request, "ideas/account.html", {
        "my_entries": Idea.objects.filter(creator=request.user, award_round__isnull=False).select_related("award_round"),
        "my_ballots": Ballot.objects.filter(voter=request.user).select_related("award_round", "idea").order_by("-updated_at"),
    })


