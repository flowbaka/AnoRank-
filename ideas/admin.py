from django.contrib import admin
from .models import Idea, Rating


@admin.register(Idea)
class IdeaAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "created_at")
    list_filter = ("category", "created_at")
    search_fields = ("title", "description")
    readonly_fields = ("public_id", "created_at")


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ("idea", "feasibility", "impact", "originality", "updated_at")
    readonly_fields = ("created_at", "updated_at")
