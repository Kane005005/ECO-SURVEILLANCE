"""
Tests for views and API endpoints.
"""
from django.test import TestCase, Client
from django.urls import reverse
from apps.incidents.models import Incident
from apps.geography.models import MonitoringZone
from django.utils import timezone
from datetime import timedelta


class IncidentViewsTest(TestCase):
    """Tests for incident views."""

    def setUp(self):
        self.client = Client()

        # Create test zone
        self.zone = MonitoringZone.objects.create(
            name="Zone Test",
            zone_type="FOREST",
            latitude=17.5,
            longitude=-3.0
        )

        # Create test incident
        self.incident = Incident.objects.create(
            title="Test Incident",
            incident_type="WILDFIRE",
            description="Test description",
            zone=self.zone,
            severity="HIGH",
            risk_score=75.0,
            confidence_score=85.0,
            detected_at=timezone.now(),
            status="NEW",
            metadata={"test": "data"}
        )

    def test_incident_list_view(self):
        """Test incident list view."""
        response = self.client.get(reverse('incidents:incident_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.incident.title)

    def test_incident_detail_view(self):
        """Test incident detail view."""
        response = self.client.get(reverse('incidents:incident_detail', args=[self.incident.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.incident.title)
        self.assertContains(response, self.incident.description)

    def test_incident_update_status(self):
        """Test incident status update."""
        response = self.client.post(
            reverse('incidents:incident_update_status', args=[self.incident.id]),
            {'status': 'INVESTIGATING'}
        )
        self.assertEqual(response.status_code, 302)  # Redirect

        # Verify status updated
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.status, 'INVESTIGATING')

    def test_incident_analyze_api(self):
        """Test incident analysis API."""
        response = self.client.post(
            reverse('incidents:incident_analyze', args=[self.incident.id]),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('success', data)


class DashboardApiTest(TestCase):
    """Tests for dashboard API endpoints."""

    def setUp(self):
        self.client = Client()

        # Create test zone
        self.zone = MonitoringZone.objects.create(
            name="Zone Test",
            zone_type="FOREST",
            latitude=17.5,
            longitude=-3.0
        )

    def test_dashboard_api(self):
        """Test main dashboard API."""
        response = self.client.get('/api/dashboard/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('zones', data)

    def test_map_api(self):
        """Test map API endpoint."""
        response = self.client.get('/api/map/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('zones', data)
        self.assertIn('fires', data)

    def test_vegetation_api(self):
        """Test vegetation API endpoint."""
        response = self.client.get('/api/vegetation/')
        self.assertEqual(response.status_code, 200)

    def test_climate_api(self):
        """Test climate API endpoint."""
        response = self.client.get('/api/climate/')
        self.assertEqual(response.status_code, 200)

    def test_iez_api(self):
        """Test IEZ API endpoint."""
        response = self.client.get('/api/iez/')
        self.assertEqual(response.status_code, 200)

    def test_air_quality_api(self):
        """Test air quality API endpoint."""
        response = self.client.get('/api/air-quality/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('air_quality', data)

    def test_risk_api(self):
        """Test risk API endpoint."""
        response = self.client.get('/api/risk/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('risks', data)

    def test_satellite_api(self):
        """Test satellite API endpoint."""
        response = self.client.get('/api/satellite/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('satellite_observations', data)


class ManagementCommandTest(TestCase):
    """Tests for management commands."""

    def test_sync_all_sources_exists(self):
        """Test sync_all_sources command exists."""
        from django.core.management import get_commands
        commands = get_commands()
        self.assertIn('sync_all_sources', commands)

    def test_sync_all_sources_help(self):
        """Test sync_all_sources command exists and is callable."""
        from django.core.management import get_commands
        commands = get_commands()
        self.assertIn('sync_all_sources', commands)
        # Verify module path
        self.assertIn('apps.core', commands['sync_all_sources'])
