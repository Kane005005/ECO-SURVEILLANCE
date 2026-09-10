import json
from django.test import TestCase, Client, override_settings
from django.core.cache import cache
from apps.cms.models import BlogPost, ProjectPortfolio, SiteSettings


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class CMSTest(TestCase):
    def setUp(self):
        self.client = Client()
        cache.clear()

        # Seed test post
        self.post = BlogPost.objects.create(
            title="Article Test Surveillance",
            category="ECOLOGY",
            summary="Résumé de l'article test",
            content="Contenu détaillé de l'article test pour ECO-SURVEILLANCE.",
            author_name="Observateur Test",
            status="PUBLISHED"
        )

        # Seed test project
        self.project = ProjectPortfolio.objects.create(
            title="Projet Test Hydrologie",
            subtitle="Sous-titre test",
            category="HYDROLOGIE",
            description="Description du projet test hydrologique.",
            partner_or_client="Partenaire Test",
            technologies_used="GloFAS, Django, Leaflet",
            demo_url="/map/",
            is_featured=True
        )

        # Seed test settings
        self.settings = SiteSettings.get_settings()

    def tearDown(self):
        cache.clear()

    def test_blog_post_model_and_slug(self):
        """Test BlogPost creation, auto-slugification and string representation."""
        self.assertIn("Article Test Surveillance", str(self.post))
        self.assertTrue(self.post.slug.startswith("article-test-surveillance"))
        self.assertIsNotNone(self.post.image_display_url)

    def test_project_portfolio_model(self):
        """Test ProjectPortfolio creation, auto-slugification and properties."""
        self.assertIn("Projet Test Hydrologie", str(self.project))
        self.assertTrue(self.project.slug.startswith("projet-test-hydrologie"))
        self.assertTrue(self.project.is_featured)

    def test_site_settings_singleton(self):
        """Test SiteSettings singleton behavior and default values."""
        settings1 = SiteSettings.get_settings()
        self.assertEqual(settings1.pk, 1)
        self.assertEqual(settings1.site_name, "ECO-SURVEILLANCE MALI")

        # Save modification and ensure pk remains 1
        settings1.site_name = "ECO-SURVEILLANCE MALI V2"
        settings1.save()
        self.assertEqual(SiteSettings.objects.count(), 1)
        self.assertEqual(SiteSettings.get_settings().site_name, "ECO-SURVEILLANCE MALI V2")

    def test_public_blog_list_view(self):
        """Test GET /blog/ returns 200 and renders blog posts."""
        response = self.client.get("/blog/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Article Test Surveillance")

    def test_public_blog_detail_view_and_view_count(self):
        """Test GET /blog/<slug>/ renders article and increments views_count."""
        initial_views = self.post.views_count
        response = self.client.get(f"/blog/{self.post.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Article Test Surveillance")

        self.post.refresh_from_db()
        self.assertEqual(self.post.views_count, initial_views + 1)

    def test_public_portfolio_list_view(self):
        """Test GET /portfolio/ returns 200 and renders projects."""
        response = self.client.get("/portfolio/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Projet Test Hydrologie")

    def test_api_cms_data(self):
        """Test GET /api/cms/data/ returns complete CMS payload for dashboard."""
        response = self.client.get("/api/cms/data/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("posts", data)
        self.assertIn("portfolio", data)
        self.assertIn("settings", data)
        self.assertGreaterEqual(len(data["posts"]), 1)
        self.assertGreaterEqual(len(data["portfolio"]), 1)

    def test_api_post_crud(self):
        """Test BlogPost create, update and delete via JSON APIs."""
        # Create
        create_payload = {
            "title": "Nouveau Post API",
            "category": "INNOVATION",
            "summary": "Résumé API",
            "content": "Contenu complet API",
            "author_name": "Ingénieur IA",
            "status": "PUBLISHED"
        }
        res_create = self.client.post(
            "/api/cms/posts/create/",
            data=json.dumps(create_payload),
            content_type="application/json"
        )
        self.assertEqual(res_create.status_code, 201)
        post_id = res_create.json()["post_id"]

        # Update
        update_payload = {"title": "Post API Modifié", "category": "FLOOD_ALERT"}
        res_update = self.client.post(
            f"/api/cms/posts/{post_id}/update/",
            data=json.dumps(update_payload),
            content_type="application/json"
        )
        self.assertEqual(res_update.status_code, 200)
        updated_post = BlogPost.objects.get(pk=post_id)
        self.assertEqual(updated_post.title, "Post API Modifié")
        self.assertEqual(updated_post.category, "FLOOD_ALERT")

        # Delete
        res_del = self.client.post(f"/api/cms/posts/{post_id}/delete/")
        self.assertEqual(res_del.status_code, 200)
        self.assertFalse(BlogPost.objects.filter(pk=post_id).exists())

    def test_api_portfolio_crud(self):
        """Test ProjectPortfolio create, update and delete via JSON APIs."""
        # Create
        create_payload = {
            "title": "Nouveau Projet API",
            "subtitle": "Sous-titre API",
            "category": "SURVEILLANCE",
            "description": "Description API",
            "partner_or_client": "Partenaire API",
            "technologies_used": "GEE, Sentinel-2",
            "is_featured": True
        }
        res_create = self.client.post(
            "/api/cms/portfolio/create/",
            data=json.dumps(create_payload),
            content_type="application/json"
        )
        self.assertEqual(res_create.status_code, 201)
        proj_id = res_create.json()["project_id"]

        # Update
        update_payload = {"title": "Projet API Renommé", "is_featured": False}
        res_update = self.client.post(
            f"/api/cms/portfolio/{proj_id}/update/",
            data=json.dumps(update_payload),
            content_type="application/json"
        )
        self.assertEqual(res_update.status_code, 200)
        updated_proj = ProjectPortfolio.objects.get(pk=proj_id)
        self.assertEqual(updated_proj.title, "Projet API Renommé")
        self.assertFalse(updated_proj.is_featured)

        # Delete
        res_del = self.client.post(f"/api/cms/portfolio/{proj_id}/delete/")
        self.assertEqual(res_del.status_code, 200)
        self.assertFalse(ProjectPortfolio.objects.filter(pk=proj_id).exists())

    def test_api_settings_update(self):
        """Test POST /api/cms/settings/update/."""
        payload = {
            "site_name": "ECO-SURVEILLANCE PLATEFORME NATIONALE",
            "contact_email": "direction@eco-surveillance.ml",
            "emergency_line": "80 00 99 99",
            "alert_banner_active": True,
            "alert_banner_text": "Alerte inondation active Delta Niger",
            "alert_banner_level": "DANGER"
        }
        response = self.client.post(
            "/api/cms/settings/update/",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        updated_settings = SiteSettings.get_settings()
        self.assertEqual(updated_settings.site_name, "ECO-SURVEILLANCE PLATEFORME NATIONALE")
        self.assertEqual(updated_settings.emergency_line, "80 00 99 99")
        self.assertTrue(updated_settings.alert_banner_active)
        self.assertEqual(updated_settings.alert_banner_level, "DANGER")
