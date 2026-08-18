from django.db import models

class Report(models.Model):
    REPORT_TYPES = [
        ("DAILY", "Quotidien"),
        ("WEEKLY", "Hebdomadaire"),
        ("MONTHLY", "Mensuel"),
        ("INCIDENT", "Incident"),
        ("ZONE", "Zone"),
    ]
    report_type = models.CharField(max_length=16, choices=REPORT_TYPES)
    title = models.CharField(max_length=255)
    zone = models.ForeignKey("geography.MonitoringZone", on_delete=models.SET_NULL, null=True, blank=True, related_name="reports")
    content = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    is_simulated = models.BooleanField(default=False)

    class Meta:
        ordering = ["-generated_at"]

    def __str__(self):
        return f"{self.get_report_type_display()}: {self.title}"
