from django.test import TestCase
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from .models import Idea, Rating
from .views import scored_ideas


class WebsiteTests(TestCase):
    def setUp(self):
        self.idea = Idea.objects.create(title="A shared neighbourhood toolbox", description="Let neighbours borrow tools from a shared collection instead of buying things they only use once.")
        self.detail = reverse("idea_detail", args=[self.idea.public_id])

    def test_pages_render_without_an_account(self):
        for name in ("home", "leaderboard", "saved", "about", "submit_idea"):
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        response = self.client.get(self.detail)
        self.assertContains(response, self.idea.title)
        self.assertContains(response, "Not rated yet")

    def test_submission_does_not_record_a_creator(self):
        user = get_user_model().objects.create_user(username="private-author", password="test-only-password")
        self.client.force_login(user)
        response = self.client.post(reverse("submit_idea"), {"title": "  A free repair cafe  ", "category": "community", "description": "Help people repair household items with volunteer support every weekend.", "creator": user.pk})
        created = Idea.objects.get(title="A free repair cafe")
        self.assertIsNone(created.creator)
        self.assertRedirects(response, reverse("idea_detail", args=[created.public_id]))
        self.assertNotContains(self.client.get(response.url), "private-author")

    def test_invalid_submission_keeps_data_and_does_not_save(self):
        response = self.client.post(reverse("submit_idea"), {"title": "Tiny", "description": "Too short", "category": "community"})
        self.assertEqual(Idea.objects.count(), 1)
        self.assertContains(response, "at least 5 characters")
        self.assertContains(response, "Too short")
        self.assertContains(self.client.post(reverse("submit_idea"), {}), "This field is required")

    def test_rating_is_updated_instead_of_counted_twice(self):
        self.client.post(self.detail, {"feasibility": 3, "impact": 4, "originality": 5})
        self.client.post(self.detail, {"feasibility": 5, "impact": 5, "originality": 5})
        self.assertEqual(Rating.objects.count(), 1)
        self.assertEqual(Rating.objects.get().feasibility, 5)
        other = Client()
        other.post(self.detail, {"feasibility": 1, "impact": 1, "originality": 1})
        idea = scored_ideas().get(pk=self.idea.pk)
        self.assertEqual(idea.rating_count, 2)
        self.assertEqual(idea.score, 3)
        self.assertContains(self.client.get(self.detail), "Update my rating")

    def test_invalid_and_incomplete_ratings_are_rejected(self):
        for values in ({"feasibility": 0, "impact": 5, "originality": 5}, {"feasibility": 6, "impact": 5, "originality": 5}, {"feasibility": 3}, {}):
            with self.subTest(values=values):
                response = self.client.post(self.detail, values)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(Rating.objects.count(), 0)

    def test_search_category_and_rank_order(self):
        school = Idea.objects.create(title="Open learning library", description="A library of resources for local students.", category="education")
        self.client.post(self.detail, {"feasibility": 2, "impact": 3, "originality": 4})
        self.client.post(reverse("idea_detail", args=[school.public_id]), {"feasibility": 5, "impact": 5, "originality": 5})
        unrated = Idea.objects.create(title="An unrated suggestion", description="A new idea without ratings yet.")
        ranked = self.client.get(reverse("leaderboard"))
        self.assertEqual([idea.pk for idea in ranked.context["page_obj"]], [school.pk, self.idea.pk])
        self.assertNotContains(ranked, unrated.title)
        response = self.client.get(reverse("home"), {"category": "education", "q": "students"})
        self.assertContains(response, school.title)
        self.assertNotContains(response, self.idea.title)

    def test_save_is_private_and_post_only(self):
        save_url = reverse("toggle_save", args=[self.idea.public_id])
        self.assertEqual(self.client.get(save_url).status_code, 405)
        self.client.post(save_url, {"next": "https://untrusted.example"})
        self.assertContains(self.client.get(reverse("saved")), self.idea.title)
        self.assertNotContains(Client().get(reverse("saved")), self.idea.title)
        response = self.client.post(save_url, {"return_to": "saved"})
        self.assertRedirects(response, reverse("saved"))
        self.assertNotContains(self.client.get(reverse("saved")), self.idea.title)

    def test_user_text_is_escaped(self):
        self.idea.title = "<script>alert('test')</script>"
        self.idea.description = "<img src=x onerror=alert('test')>"
        self.idea.save()
        response = self.client.get(self.detail)
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, "<script>alert")
        self.assertNotContains(response, "<img src=x")

    def test_post_requires_csrf_and_missing_idea_returns_404(self):
        self.assertEqual(Client(enforce_csrf_checks=True).post(self.detail, {"feasibility": 5, "impact": 5, "originality": 5}).status_code, 403)
        self.assertEqual(self.client.get(reverse("idea_detail", args=["00000000-0000-0000-0000-000000000000"])).status_code, 404)

    def test_pagination_keeps_search_and_category(self):
        for n in range(12):
            Idea.objects.create(title=f"Education idea {n}", description="A considered way to improve learning.", category="education")
        response = self.client.get(reverse("home"), {"q": "Education", "category": "education", "sort": "top", "page": 2})
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertEqual(len(response.context["page_obj"]), 3)
        self.assertContains(response, "category=education")
