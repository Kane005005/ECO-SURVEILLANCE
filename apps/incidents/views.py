from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from .models import Incident

def incident_list_view(request):
    incidents = Incident.objects.select_related("zone", "assigned_to").order_by("-detected_at")[:200]
    return render(request, "incidents/incident_list.html", {"incidents": incidents})

def incident_detail_view(request, pk):
    incident = get_object_or_404(Incident.objects.select_related("zone", "assigned_to", "anomaly"), pk=pk)
    return render(request, "incidents/incident_detail.html", {"incident": incident})

@csrf_exempt
@require_POST
def incident_analyze_api(request, pk):
    """Analyze incident with Groq AI and return recommendations."""
    incident = get_object_or_404(Incident, pk=pk)
    
    try:
        from ai.groq import GroqProvider
        from django.conf import settings
        
        provider = GroqProvider(api_key=getattr(settings, 'GROQ_API_KEY', None))
        
        # Build context for AI analysis
        context = {
            "incident": {
                "title": incident.title,
                "type": incident.get_incident_type_display(),
                "severity": incident.get_severity_display(),
                "description": incident.description,
                "risk_score": incident.risk_score,
                "confidence_score": incident.confidence_score,
                "zone": incident.zone.name,
                "zone_type": incident.zone.zone_type if hasattr(incident.zone, 'zone_type') else "unknown",
                "detected_at": incident.detected_at.isoformat() if incident.detected_at else None,
                "source": incident.source,
                "metadata": incident.metadata,
            },
            "analysis_type": "incident_interpretation"
        }
        
        result = provider.interpret_incident(context)
        
        return JsonResponse({
            "success": True,
            "summary": result.get("summary", ""),
            "model": result.get("model", ""),
        })
        
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

@require_POST
def incident_update_status_view(request, pk):
    """Update incident status."""
    incident = get_object_or_404(Incident, pk=pk)
    new_status = request.POST.get('status')
    
    if new_status in dict(Incident.STATUS_CHOICES):
        incident.status = new_status
        incident.save()
    
    return redirect('incidents:incident_detail', pk=pk)
