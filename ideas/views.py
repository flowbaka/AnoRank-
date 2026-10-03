import uuid

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Avg, Count, ExpressionWrapper, F, FloatField, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import IdeaForm, RatingForm
from .models import Idea, Rating


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
    })


def submit_idea(request):
    form = IdeaForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        idea = form.save(commit=False)
        idea.creator = None
        idea.save()
        messages.success(request, "Your idea is live. Let the idea speak for itself.")
        return redirect("idea_detail", public_id=idea.public_id)
    return render(request, "ideas/submit.html", {"form": form, "mode": "submit"})


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


