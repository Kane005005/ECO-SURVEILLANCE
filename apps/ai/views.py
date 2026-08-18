from django.shortcuts import render
from .models import AIAnalysis

def ai_analysis_view(request):
    analyses = AIAnalysis.objects.select_related("incident").order_by("-created_at")[:50]
    return render(request, "ai/ai_analysis.html", {"analyses": analyses})
