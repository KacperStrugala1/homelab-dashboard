from django import forms

from .models import Service


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ["name", "address", "port", "url_name", "is_online"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input", "placeholder": "Service name"}),
            "address": forms.TextInput(attrs={"class": "input", "placeholder": "192.168.1.10"}),
            "port": forms.NumberInput(attrs={"class": "input", "placeholder": "8080"}),
            "url_name": forms.URLInput(attrs={"class": "input", "placeholder": "https://example.local"}),
            "is_online": forms.CheckboxInput(attrs={"class": "checkbox"}),
        }