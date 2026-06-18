from django import forms

from .models import Category, Service


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input", "placeholder": "Category name"}),
        }


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ["name", "category", "address", "port", "url_name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input", "placeholder": "Service name"}),
            "category": forms.Select(attrs={"class": "input"}),
            "address": forms.TextInput(attrs={"class": "input", "placeholder": "192.168.1.10"}),
            "port": forms.NumberInput(attrs={"class": "input", "placeholder": "8080"}),
            "url_name": forms.URLInput(attrs={"class": "input", "placeholder": "https://example.local"}),
        }