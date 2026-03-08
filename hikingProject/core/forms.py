from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, HikingEvent

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
