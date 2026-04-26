from django.contrib import admin
from django.urls import path
from . import views
from django.views import View

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.HomeView.as_view(), name="homepage")
]
