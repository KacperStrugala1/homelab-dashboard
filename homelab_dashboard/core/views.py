from django.shortcuts import render
from django.views import View
from .models import Service, MediaPanel

class HomeView(View):
    template_name = "dashboard.html"
    services = Service.objects.all()
    media_panels = MediaPanel.objects.all()
    
    def get(self, request):
        return render(request, self.template_name, {"services": self.services, "media_panels": self.media_panels})