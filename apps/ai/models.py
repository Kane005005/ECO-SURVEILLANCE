from django.db import models

class AIAnalysis(models.Model):
    incident = models.ForeignKey("incidents.Incident", on_delete=models.CASCADE, related_name="ai_analyses", null=True, blank=True)
    provider = models.CharField(max_length=64)
    model = models.CharField(max_length=128)
    input_summary = models.JSONField(default=dict, blank=True)
    output = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Analyse IA"
        verbose_name_plural = "Analyses IA"

    def __str__(self):
        return f"AI Analysis ({self.provider}/{self.model}) at {self.created_at}"
