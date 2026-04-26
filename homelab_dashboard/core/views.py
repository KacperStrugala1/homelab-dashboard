from django.shortcuts import render
from django.views import View
from .models import Service

class HomeView(View):
    template_name = "dashboard.html"
    services = Service.objects.all()
    
    def get(self, request):
        return render(request, self.template_name, {"services": self.services})