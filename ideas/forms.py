from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import Idea, Rating


class IdeaForm(forms.ModelForm):
    class Meta:
        model = Idea
        fields = ["title", "category", "description"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Give your idea a clear, memorable title", "maxlength": 255}),
            "description": forms.Textarea(attrs={"rows": 8, "placeholder": "What problem does it solve? How would it work? Who would it help?", "maxlength": 10000}),
        }
        labels = {"description": "Tell us about your idea"}

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if len(title) < 5:
            raise forms.ValidationError("Use at least 5 characters for a clear title.")
        return title

    def clean_description(self):
        description = self.cleaned_data["description"].strip()
        if len(description) < 30:
            raise forms.ValidationError("Add at least 30 characters so people can understand your idea.")
        if len(description) > 10000:
            raise forms.ValidationError("Keep your description under 10,000 characters.")
        return description


class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ["feasibility", "impact", "originality"]
        widgets = {name: forms.RadioSelect(choices=[(n, str(n)) for n in range(1, 6)]) for name in fields}


class CommunitySignupForm(UserCreationForm):
    email = forms.EmailField(label="Email", help_text="Used privately by organisers to contact an award winner.")

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "email")

    def clean_username(self):
        username = self.cleaned_data["username"]
        if get_user_model().objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account already uses this email. Sign in to that account.")
        return email
