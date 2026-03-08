from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import *
import datetime as dt

class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "password1", "password2", "gender",  "name", "location", "experience_level", "profile_picture", "pace")

class HikingEventForm(forms.ModelForm):
    class Meta:
        model = HikingEvent
        fields = [
                "title",
                "location",
                "gpx_file",
                "date",
                "time",
                "pace",
                "recommended_experience",
                "mileage",
                "elevation_gain",
                "visibility",
                "description",
                "max_participants",
                ] 
        widgets = {
                "title": forms.TextInput(attrs={
                    "placeholder": "Enter hike title"
                    }),
                "location": forms.TextInput(attrs={
                    "placeholder": "Enter location"
                    }),
                "gpx_file": forms.ClearableFileInput(attrs={
                    "accept": ".gpx"
                    }),
                "date": forms.DateInput(attrs={
                    "type": "date"
                    }),
                "time": forms.TimeInput(attrs={
                    "type": "time"
                    }),
                "description": forms.Textarea(attrs={
                    "rows": 4,
                    "placeholder": "Add any details about the hike"
                    }),
                "mileage": forms.NumberInput(attrs={
                    "step": "0.1",
                    "placeholder": "e.g. 5.5"
                    }),
                "elevation_gain": forms.NumberInput(attrs={
                    "placeholder": "e.g. 1200"
                    }),
                "max_participants": forms.NumberInput(attrs={
                    "placeholder": "Leave blank for no limit"
                    }),
                }
        labels = {
                "recommended_experience": "Recommended Experience",
                "elevation_gain": "Elevation Gain (ft)",
                "max_participants": "Max Participants",
                }
        help_texts = {
                "visibility": "Choose who can see this event.",
                "max_participants": "Optional.",
                }

    def clean_mileage(self):
        mileage = self.cleaned_data["mileage"]
        if mileage <= 0:
            raise forms.ValidationError("Mileage must be greater than 0.")
        return mileage

    def clean_elevation_gain(self):
        elevation_gain = self.cleaned_data["elevation_gain"]
        if elevation_gain < 0:
            raise forms.ValidationError("Elevation gain cannot be negative.")
        return elevation_gain

    def clean_max_participants(self):
        max_participants = self.cleaned_data.get("max_participants")
        if max_participants is not None and max_participants <= 0:
            raise forms.ValidationError("Max participants must be greater than 0.")
        return max_participants

    def clean_date(self):
        date = self.cleaned_data.get("date") 
        today = dt.date.today()
        if date.year < today.year or (date.year == today.year and date.month < today.month) or (date.year == today.year and date.month == today.month and date.day < today.day):
            raise forms.ValidationError("Must choose future date")
        return date
    
from django import forms
from .models import HikingEvent


class SearchForm(forms.Form):
    TAB_CHOICES = [
        ("hikes", "Hikes"),
        ("users", "Users"),
    ]

    q = forms.CharField(
        required=False,
        label="",
        widget=forms.TextInput(attrs={"placeholder": "Search..."})
    )

    tab = forms.ChoiceField(
        choices=TAB_CHOICES,
        required=False,
        widget=forms.HiddenInput()
    )

    pace = forms.ChoiceField(
        required=False,
        choices=[("", "Any pace")] + list(HikingEvent.PACES)
    )

    experience = forms.ChoiceField(
        required=False,
        choices=[("", "Any experience")] + list(HikingEvent.EXPERIENCE_LEVELS)
    )

    date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"})
    )

    max_mileage = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={
            "placeholder": "Max mileage",
            "step": "0.1",
            "min": "0",
        })
    )

    location = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Location"})
    )

    gender = forms.ChoiceField(
        required=False,
        choices=[("", "Any gender")] + list(User.GENDER)
    )

    min_age = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            "placeholder": "Min age",
            "min": "0",
        })
    )

    max_age = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            "placeholder": "Max age",
            "min": "0",
        })
    )

    user_experience = forms.ChoiceField(
        required=False,
        choices=[("", "Any experience")] + list(User.EXPERIENCE_LEVEL)
    )

    user_pace = forms.ChoiceField(
        required=False,
        choices=[("", "Any pace")] + list(User.PACE)
    )

class EditProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            "name",
            "location",
            "gender",
            "experience_level",
            "profile_picture",
            "pace",
        )

class ReportUserForm(forms.Form):
    reason = forms.ChoiceField(choices=[
        ("harassment", "Harassment"),
        ("fake", "Fake Account"),
        ("other", "Other"),
    ])
    details = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 4})
    )

class HikeMessageForm(forms.ModelForm):
    class Meta:
        model = HikeMessage
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Write a message..."
            })
        }
        labels = {
            "content": ""
        }
