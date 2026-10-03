from datetime import timedelta
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import AwardRound, Ballot, Idea, Rating
from .services import cast_ballot, standings


class AwardTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.round = AwardRound.objects.create(
            title="Better days at BIC", description="Ideas to improve our community.",
            submissions_open_at=self.now - timedelta(days=2),
            voting_starts_at=self.now - timedelta(days=1),
            voting_ends_at=self.now + timedelta(days=1),
        )
        self.user = get_user_model().objects.create_user(username="a-member", email="member@example.test", password="Test-only-password-328")
        self.other = get_user_model().objects.create_user(username="another-member", email="another@example.test", password="Test-only-password-723")
        self.entry = Idea.objects.create(title="A campus repair cafe", description="Let students help each other repair everyday items instead of replacing them.", award_round=self.round, creator=self.user)
        self.second = Idea.objects.create(title="A shared book shelf", description="Share used textbooks with other students in the community.", award_round=self.round, creator=self.other)
        self.vote_url = reverse("vote", args=[self.round.public_id, self.entry.public_id])

    def test_public_award_pages_render_without_identities(self):
        for url in (reverse("awards"), reverse("award_detail", args=[self.round.public_id]), reverse("idea_detail", args=[self.entry.public_id])):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, self.user.username)
            self.assertNotContains(response, self.user.email)
        self.assertContains(self.client.get(reverse("award_detail", args=[self.round.public_id])), "One vote per account")

    def test_signed_in_account_can_vote_and_move_its_ballot(self):
        self.assertEqual(self.client.post(self.vote_url).status_code, 302)
        self.assertEqual(Ballot.objects.count(), 0)
        self.client.force_login(self.user)
        self.client.post(self.vote_url)
        self.client.post(reverse("vote", args=[self.round.public_id, self.second.public_id]))
        self.assertEqual(Ballot.objects.count(), 1)
        self.assertEqual(Ballot.objects.get().idea_id, self.second.pk)
        entries, winners = standings(self.round)
        self.assertEqual([(entry.pk, entry.vote_count) for entry in entries], [(self.second.pk, 1), (self.entry.pk, 0)])
        self.assertEqual(winners, [])

    def test_one_ballot_constraint_and_other_rounds(self):
        cast_ballot(self.user, self.round.pk, self.entry.pk)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Ballot.objects.create(award_round=self.round, idea=self.second, voter=self.user)
        other_round = AwardRound.objects.create(title="Another round", description="Another opportunity.", submissions_open_at=self.now - timedelta(days=3), voting_starts_at=self.now - timedelta(days=2), voting_ends_at=self.now + timedelta(days=2))
        other_entry = Idea.objects.create(title="A separate idea", description="An idea for another round.", award_round=other_round, creator=self.user)
        cast_ballot(self.user, other_round.pk, other_entry.pk)
        self.assertEqual(Ballot.objects.count(), 2)

    def test_voting_window_and_deadline_are_enforced_on_the_server(self):
        for at_time in (self.round.voting_starts_at - timedelta(seconds=1), self.round.voting_ends_at, self.round.voting_ends_at + timedelta(days=1)):
            with self.subTest(at_time=at_time), patch("ideas.models.timezone.now", return_value=at_time):
                with self.assertRaises(ValidationError):
                    cast_ballot(self.user, self.round.pk, self.entry.pk)
        with patch("ideas.models.timezone.now", return_value=self.round.voting_starts_at):
            cast_ballot(self.user, self.round.pk, self.entry.pk)
        with patch("ideas.models.timezone.now", return_value=self.round.voting_ends_at):
            self.client.force_login(self.user)
            self.client.post(reverse("vote", args=[self.round.public_id, self.second.public_id]))
        self.assertEqual(Ballot.objects.get().idea_id, self.entry.pk)

    def test_cross_round_vote_is_rejected(self):
        general = Idea.objects.create(title="Outside the award", description="This belongs to the open board.")
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(reverse("vote", args=[self.round.public_id, general.public_id])).status_code, 404)
        with self.assertRaises(ValidationError):
            cast_ballot(self.user, self.round.pk, general.pk)
        invalid = Ballot(award_round=self.round, idea=general, voter=self.user)
        with self.assertRaises(ValidationError):
            invalid.clean()

    def test_final_result_uses_votes_and_shared_winners_for_ties(self):
        Rating.objects.create(idea=self.second, voter_id="00000000-0000-0000-0000-000000000001", feasibility=5, impact=5, originality=5)
        cast_ballot(self.user, self.round.pk, self.entry.pk)
        with patch("ideas.models.timezone.now", return_value=self.round.voting_ends_at):
            entries, winners = standings(self.round)
            self.assertEqual([entry.pk for entry in winners], [self.entry.pk])
        cast_ballot(self.other, self.round.pk, self.second.pk)
        with patch("ideas.models.timezone.now", return_value=self.round.voting_ends_at):
            entries, winners = standings(self.round)
            self.assertEqual({entry.pk for entry in winners}, {self.entry.pk, self.second.pk})
            response = self.client.get(reverse("award_detail", args=[self.round.public_id]))
            self.assertContains(response, "joint winners")
        Ballot.objects.all().delete()
        with patch("ideas.models.timezone.now", return_value=self.round.voting_ends_at):
            self.assertEqual(standings(self.round)[1], [])
            self.assertContains(self.client.get(reverse("award_detail", args=[self.round.public_id])), "No award winner")

    def test_award_entry_requires_an_account_and_submission_window(self):
        submit_url = reverse("award_submit", args=[self.round.public_id])
        self.assertRedirects(self.client.get(submit_url), reverse("login") + "?next=" + submit_url)
        self.client.force_login(self.user)
        data = {"title": "A safer campus crossing", "category": "community", "description": "Add a marked crossing and better lighting to the main campus entrance."}
        self.client.post(submit_url, data)
        self.assertFalse(Idea.objects.filter(title=data["title"]).exists())
        with patch("ideas.models.timezone.now", return_value=self.round.submissions_open_at):
            response = self.client.post(submit_url, data)
        created = Idea.objects.get(title=data["title"])
        self.assertEqual(created.creator_id, self.user.pk)
        self.assertEqual(created.award_round_id, self.round.pk)
        self.assertRedirects(response, reverse("idea_detail", args=[created.public_id]))

    def test_sign_up_login_and_private_account(self):
        response = self.client.post(reverse("signup"), {"username": "new-member", "email": "new@example.test", "password1": "Birch!Orbit92river", "password2": "Birch!Orbit92river"})
        self.assertRedirects(response, reverse("awards"))
        self.assertTrue(get_user_model().objects.filter(username="new-member").exists())
        self.assertContains(self.client.get(reverse("account")), "new@example.test")
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.client.post(reverse("logout"))
        self.assertEqual(self.client.get(reverse("account")).status_code, 302)
        self.client.post(reverse("login"), {"username": "new-member", "password": "Birch!Orbit92river", "next": "https://untrusted.example/"})
        self.assertRedirects(self.client.get(reverse("login")), reverse("awards"))
        self.client.post(reverse("logout"))
        response = self.client.post(reverse("signup"), {"username": "NEW-MEMBER", "email": "NEW@example.test", "password1": "Birch!Orbit92river", "password2": "Birch!Orbit92river"})
        self.assertContains(response, "already taken")
        self.assertContains(response, "already uses this email")

    def test_private_account_only_shows_own_entries_and_votes(self):
        self.client.force_login(self.user)
        cast_ballot(self.user, self.round.pk, self.entry.pk)
        response = self.client.get(reverse("account"))
        self.assertContains(response, self.entry.title)
        self.assertNotContains(response, self.second.title)
        self.assertNotContains(response, self.other.email)

    def test_votes_require_post_and_csrf(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.vote_url).status_code, 405)
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.user)
        self.assertEqual(strict.post(self.vote_url).status_code, 403)

    def test_round_windows_validate_and_admin_locks_results(self):
        self.round.voting_ends_at = self.round.voting_starts_at
        with self.assertRaises(ValidationError):
            self.round.full_clean()
        self.round.refresh_from_db()
        staff = get_user_model().objects.create_superuser(username="organiser", email="staff@example.test", password="Test-only-8483-password")
        request = RequestFactory().get("/admin/")
        request.user = staff
        self.assertFalse(admin.site._registry[Idea].has_change_permission(request, self.entry))
        self.assertFalse(admin.site._registry[Idea].has_delete_permission(request, self.entry))
        readonly = admin.site._registry[AwardRound].get_readonly_fields(request, self.round)
        self.assertIn("voting_ends_at", readonly)
        self.assertIn("award", readonly)
        ballot, _ = cast_ballot(self.user, self.round.pk, self.entry.pk)
        self.assertFalse(admin.site._registry[Ballot].has_change_permission(request, ballot))
        self.assertFalse(admin.site._registry[Ballot].has_delete_permission(request, ballot))
        with self.assertRaises(ProtectedError):
            self.entry.delete()
        self.client.force_login(staff)
        self.assertEqual(self.client.get(reverse("admin:ideas_awardround_change", args=[self.round.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:ideas_ballot_change", args=[ballot.pk])).status_code, 200)
