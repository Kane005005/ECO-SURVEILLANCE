from decimal import Decimal
from core.services.anomaly import AnomalyEngine
from .models import Anomaly
from django.utils import timezone
import logging

logger = logging.getLogger("apps.anomalies")

class AnomalyDetectionService:
    def __init__(self):
        self.engine = AnomalyEngine()

    def detect_from_observations(self, zone, observations, anomaly_type, source):
        anomalies = []
        for obs in observations:
            if obs.baseline_value is not None and obs.std_dev is not None and obs.std_dev > 0:
                result = self.engine.detect(
                    metric=obs.metric if hasattr(obs, 'metric') else obs.index_name,
                    current=Decimal(str(obs.value)),
                    baseline=Decimal(str(obs.baseline_value)),
                    std_dev=Decimal(str(obs.std_dev)),
                )
                if result.detected:
                    anomaly = Anomaly(
                        anomaly_type=anomaly_type,
                        zone=zone,
                        source=source,
                        detected_at=timezone.now(),
                        severity=result.severity,
                        score=min(float(abs(result.z_score)) * 10, 100),
                        confidence=min(float(abs(result.z_score)) / 4.0, 1.0),
                        metric=result.metric,
                        current_value=obs.value,
                        baseline_value=obs.baseline_value,
                        z_score=float(result.z_score),
                        status="NEW",
                        is_simulated=getattr(obs, 'is_simulated', False),
                        data=result.details,
                    )
                    anomalies.append(anomaly)
        if anomalies:
            Anomaly.objects.bulk_create(anomalies)
            logger.info("Detected %d anomalies for zone %s", len(anomalies), zone.name)
        return anomalies
