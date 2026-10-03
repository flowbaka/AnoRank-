from django.urls import path
from .import views


urlpatterns = [
    path("", views.home, name="home"),
    path("submit/", views.submit_idea, name="submit_idea"),
    path("leaderboard/", views.home, {"mode": "leaderboard"}, name="leaderboard"),
    path("saved/", views.home, {"mode": "saved"}, name="saved"),
    path("how-it-works/", views.about, name="about"),
    path("ideas/<uuid:public_id>/", views.idea_detail, name="idea_detail"),
    path("ideas/<uuid:public_id>/save/", views.toggle_save, name="toggle_save"),
]

