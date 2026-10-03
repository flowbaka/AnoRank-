from django.urls import path
from django.contrib.auth import views as auth_views
from .import views


urlpatterns = [
    path("", views.home, name="home"),
    path("submit/", views.submit_idea, name="submit_idea"),
    path("leaderboard/", views.home, {"mode": "leaderboard"}, name="leaderboard"),
    path("saved/", views.home, {"mode": "saved"}, name="saved"),
    path("how-it-works/", views.about, name="about"),
    path("ideas/<uuid:public_id>/", views.idea_detail, name="idea_detail"),
    path("ideas/<uuid:public_id>/save/", views.toggle_save, name="toggle_save"),
    path("awards/", views.award_list, name="awards"),
    path("awards/<uuid:round_id>/", views.award_detail, name="award_detail"),
    path("awards/<uuid:round_id>/submit/", views.submit_idea, name="award_submit"),
    path("awards/<uuid:round_id>/vote/<uuid:public_id>/", views.vote, name="vote"),
    path("join/", views.signup, name="signup"),
    path("login/", auth_views.LoginView.as_view(template_name="ideas/login.html", redirect_authenticated_user=True), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("account/", views.account, name="account"),
]

