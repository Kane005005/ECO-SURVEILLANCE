"""
Management command to sync data from all external sources.
"""
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import time


class Command(BaseCommand):
    help = 'Sync data from all external sources (FIRMS, POWER, Sentinel-2, Sentinel-5P)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            choices=['firms', 'power', 'sentinel2', 'sentinel5p', 'glofas', 'lance_flood', 'eco_engine', 'all'],
            default='all',
            help='Source to sync (default: all)'
        )
        parser.add_argument(
            '--zones',
            nargs='+',
            type=int,
            help='Specific zone IDs to sync (default: all zones)'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to look back (default: 30)'
        )
        parser.add_argument(
            '--async',
            action='store_true',
            dest='use_async',
            help='Run tasks asynchronously via Celery'
        )

    def handle(self, *args, **options):
        source = options['source']
        zone_ids = options['zones']
        days = options['days']
        use_async = options['use_async']

        self.stdout.write(self.style.SUCCESS(f'Starting sync for source: {source}'))
        self.stdout.write(f'Date range: {timezone.now().date() - timedelta(days=days)} to {timezone.now().date()}')
        if zone_ids:
            self.stdout.write(f'Zones: {zone_ids}')
        else:
            self.stdout.write('Zones: All zones')

        start_time = time.time()
        results = {}

        try:
            if source in ['firms', 'all']:
                self.stdout.write('\n--- Syncing FIRMS fire data ---')
                if use_async:
                    from apps.fires.tasks import sync_firms_data
                    result = sync_firms_data.delay()
                    results['firms'] = {'task_id': result.id, 'status': 'queued'}
                else:
                    results['firms'] = self._sync_firms(zone_ids, days)

            if source in ['power', 'all']:
                self.stdout.write('\n--- Syncing NASA POWER climate data ---')
                if use_async:
                    from apps.climate.tasks import sync_nasa_power
                    result = sync_nasa_power.delay()
                    results['power'] = {'task_id': result.id, 'status': 'queued'}
                else:
                    results['power'] = self._sync_power(zone_ids, days)

            if source in ['sentinel2', 'all']:
                self.stdout.write('\n--- Syncing Sentinel-2 vegetation data ---')
                if use_async:
                    from apps.vegetation.tasks import sync_sentinel2_vegetation
                    result = sync_sentinel2_vegetation.delay(zone_ids=zone_ids)
                    results['sentinel2'] = {'task_id': result.id, 'status': 'queued'}
                else:
                    results['sentinel2'] = self._sync_sentinel2(zone_ids, days)

            if source in ['sentinel5p', 'all']:
                self.stdout.write('\n--- Syncing Sentinel-5P atmospheric data ---')
                if use_async:
                    from apps.atmosphere.tasks import sync_sentinel5p_atmospheric
                    result = sync_sentinel5p_atmospheric.delay(zone_ids=zone_ids)
                    results['sentinel5p'] = {'task_id': result.id, 'status': 'queued'}
                else:
                    results['sentinel5p'] = self._sync_sentinel5p(zone_ids, days)

            if source in ['glofas', 'all']:
                self.stdout.write('\n--- Syncing Copernicus GloFAS hydrology forecasts ---')
                if use_async:
                    from apps.water.tasks import sync_glofas_hydrology
                    result = sync_glofas_hydrology.delay()
                    results['glofas'] = {'task_id': result.id, 'status': 'queued'}
                else:
                    results['glofas'] = self._sync_glofas()

            if source in ['lance_flood', 'all']:
                self.stdout.write('\n--- Syncing NASA LANCE Flood VIIRS NRT3 observations ---')
                if use_async:
                    from apps.water.tasks import sync_lance_flood
                    result = sync_lance_flood.delay()
                    results['lance_flood'] = {'task_id': result.id, 'status': 'queued'}
                else:
                    results['lance_flood'] = self._sync_lance_flood()

            if source in ['eco_engine', 'all']:
                self.stdout.write('\n--- Running ECO Engine Multi-Source Cross-Correlations ---')
                if use_async:
                    from apps.alerts.tasks import run_eco_engine
                    result = run_eco_engine.delay()
                    results['eco_engine'] = {'task_id': result.id, 'status': 'queued'}
                else:
                    results['eco_engine'] = self._run_eco_engine()

        except Exception as e:
            raise CommandError(f'Sync failed: {e}')

        elapsed = time.time() - start_time

        self.stdout.write(self.style.SUCCESS(f'\n=== Sync Complete ==='))
        self.stdout.write(f'Duration: {elapsed:.2f} seconds')

        for source_name, result in results.items():
            self.stdout.write(f'\n{source_name.upper()}:')
            if isinstance(result, dict) and 'task_id' in result:
                self.stdout.write(f'  Task ID: {result["task_id"]}')
                self.stdout.write(f'  Status: Queued for async processing')
            else:
                self.stdout.write(f'  Status: {result.get("status", "unknown")}')
                if 'total_observations' in result:
                    self.stdout.write(f'  Observations saved: {result["total_observations"]}')

    def _get_zones(self, zone_ids):
        """Get zones by IDs or all zones."""
        from apps.geography.models import MonitoringZone
        if zone_ids:
            return MonitoringZone.objects.filter(id__in=zone_ids)
        return MonitoringZone.objects.all()

    def _sync_firms(self, zone_ids, days):
        """Sync FIRMS data synchronously."""
        from data_providers.firms import FIRMSProvider

        provider = FIRMSProvider(
            map_key=getattr(settings, "FIRMS_MAP_KEY", ""),
            source=getattr(settings, "FIRMS_SOURCE", "VIIRS"),
        )

        health = provider.health_check()
        if health.status != "ok":
            return {"status": "skipped", "reason": health.reason}

        try:
            items = provider.fetch(country="MLI", days=min(days, 10))
            total_saved = 0
            for item in items:
                normalized = provider.normalize(item)
                saved = provider.save(normalized)
                total_saved += saved
            provider.close()
            return {"status": "ok", "total_observations": total_saved}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _sync_power(self, zone_ids, days):
        """Sync NASA POWER data synchronously."""
        from data_providers.nasa_power import NASAPowerProvider

        provider = NASAPowerProvider()
        zones = self._get_zones(zone_ids)

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        total_saved = 0
        zones_synced = 0

        for zone in zones:
            try:
                if not zone.latitude or not zone.longitude:
                    continue
                results = provider.fetch(
                    latitude=zone.latitude,
                    longitude=zone.longitude,
                    start_date=start_date.strftime("%Y%m%d"),
                    end_date=end_date.strftime("%Y%m%d"),
                )
                for result in results:
                    normalized = provider.normalize(result)
                    saved = provider.save(normalized)
                    total_saved += saved
                    if saved > 0:
                        zones_synced += 1
                        self.stdout.write(f'  Synced {saved} climate obs for zone {zone.name}')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  Failed POWER for {zone.name}: {e}'))

        provider.close()
        return {"synced_zones": zones_synced, "total_observations": total_saved, "status": "success"}

    def _sync_sentinel2(self, zone_ids, days):
        """Sync Sentinel-2 data synchronously."""
        from data_providers.sentinel2 import Sentinel2Provider

        provider = Sentinel2Provider(
            client_id=getattr(settings, "CDSE_CLIENT_ID", ""),
            client_secret=getattr(settings, "CDSE_CLIENT_SECRET", ""),
        )
        zones = self._get_zones(zone_ids)

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        total_saved = 0
        zones_synced = 0

        for zone in zones:
            try:
                aoi = {
                    "west": zone.longitude - 0.5 if zone.longitude else -12.0,
                    "south": zone.latitude - 0.5 if zone.latitude else 10.0,
                    "east": zone.longitude + 0.5 if zone.longitude else 4.0,
                    "north": zone.latitude + 0.5 if zone.latitude else 25.0,
                }
                fetched = provider.fetch(
                    aoi=aoi, start_date=start_date.isoformat(), end_date=end_date.isoformat(),
                    bands=["B03", "B04", "B08", "B11", "B12"], max_cloud_cover=30,
                )
                if fetched:
                    all_normalized = []
                    for result in fetched:
                        all_normalized.extend(provider.normalize(result))
                    saved_count = provider.save(all_normalized)
                    total_saved += saved_count
                    if saved_count > 0:
                        zones_synced += 1
                        self.stdout.write(f'  Synced {saved_count} vegetation obs for zone {zone.name}')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  Failed Sentinel-2 for {zone.name}: {e}'))

        return {"synced_zones": zones_synced, "total_observations": total_saved, "status": "success"}

    def _sync_sentinel5p(self, zone_ids, days):
        """Sync Sentinel-5P data synchronously."""
        from data_providers.sentinel5p import Sentinel5PProvider

        provider = Sentinel5PProvider(
            client_id=getattr(settings, "CDSE_CLIENT_ID", ""),
            client_secret=getattr(settings, "CDSE_CLIENT_SECRET", ""),
        )
        zones = self._get_zones(zone_ids)
        variables = ["SO2", "O3", "NO2", "AER_AI"]

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=min(days, 5))

        total_saved = 0
        zones_synced = 0

        for zone in zones:
            try:
                aoi = {
                    "west": zone.longitude - 0.5 if zone.longitude else -12.0,
                    "south": zone.latitude - 0.5 if zone.latitude else 10.0,
                    "east": zone.longitude + 0.5 if zone.longitude else 4.0,
                    "north": zone.latitude + 0.5 if zone.latitude else 25.0,
                }
                zone_saved = 0
                for variable in variables:
                    fetched = provider.fetch(
                        product_key=variable, aoi=aoi,
                        start_date=start_date.isoformat(), end_date=end_date.isoformat(),
                    )
                    if fetched:
                        all_normalized = []
                        for result in fetched:
                            all_normalized.extend(provider.normalize(result))
                        zone_saved += provider.save(all_normalized)

                total_saved += zone_saved
                if zone_saved > 0:
                    zones_synced += 1
                    self.stdout.write(f'  Synced {zone_saved} atmospheric obs for zone {zone.name}')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  Failed Sentinel-5P for {zone.name}: {e}'))

        return {"synced_zones": zones_synced, "total_observations": total_saved, "status": "success"}

    def _sync_glofas(self):
        """Sync Copernicus GloFAS hydrology forecasts."""
        from data_providers.glofas import GloFASProvider

        provider = GloFASProvider(
            cds_url=getattr(settings, "CDS_API_URL", "https://ewds.climate.copernicus.eu/api"),
            cds_key=getattr(settings, "CDS_API_KEY", ""),
        )
        health = provider.health_check()
        if health.status != "ok":
            return {"status": "skipped", "reason": health.reason}

        try:
            items = provider.fetch()
            saved = provider.save(provider.normalize(items))
            provider.close()
            self.stdout.write(f'  Synced {saved} GloFAS river forecasts')
            return {"status": "ok", "total_observations": saved}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _sync_lance_flood(self):
        """Sync NASA LANCE Flood VIIRS observations."""
        from data_providers.lance_flood import LANCEFloodProvider

        provider = LANCEFloodProvider(
            earthdata_token=getattr(settings, "EARTHDATA_TOKEN", ""),
            base_url=getattr(settings, "LANCE_FLOOD_BASE_URL", ""),
        )
        health = provider.health_check()
        if health.status != "ok":
            return {"status": "skipped", "reason": health.reason}

        try:
            items = provider.fetch()
            saved = provider.save(provider.normalize(items))
            provider.close()
            self.stdout.write(f'  Synced {saved} LANCE flood observations')
            return {"status": "ok", "total_observations": saved}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _run_eco_engine(self):
        """Run ECO Engine central multi-source cross-correlations."""
        from core.services.eco_engine import ECOEngine

        engine = ECOEngine()
        try:
            alerts = engine.run_all_correlations()
            self.stdout.write(f'  ECO Engine generated {len(alerts)} correlated alerts')
            return {"status": "ok", "total_observations": len(alerts)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

