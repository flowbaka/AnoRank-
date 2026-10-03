from django.contrib import admin
from .models import AwardRound, Ballot, Idea, Rating


@admin.register(Idea)
class IdeaAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "award_round", "creator", "created_at")
    list_filter = ("category", "award_round", "created_at")
    search_fields = ("title", "description")
    readonly_fields = ("public_id", "created_at", "award_round")
    actions = None

    def has_change_permission(self, request, obj=None):
        if obj and obj.award_round_id:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.award_round_id:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ("idea", "feasibility", "impact", "originality", "updated_at")
    readonly_fields = ("created_at", "updated_at")


@admin.register(AwardRound)
class AwardRoundAdmin(admin.ModelAdmin):
    list_display = ("title", "award", "voting_starts_at", "voting_ends_at")
    readonly_fields = ("public_id", "created_at")
    actions = None

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.entries.exists():
            return tuple(field.name for field in self.model._meta.fields)
        return self.readonly_fields

    def has_delete_permission(self, request, obj=None):
        if obj and obj.entries.exists():
            return False
        return super().has_delete_permission(request, obj)


@admin.register(Ballot)
class BallotAdmin(admin.ModelAdmin):
    list_display = ("award_round", "idea", "voter", "updated_at")
    list_filter = ("award_round",)
    readonly_fields = tuple(field.name for field in Ballot._meta.fields)
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
