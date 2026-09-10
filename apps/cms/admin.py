from django.contrib import admin
from .models import BlogPost, ProjectPortfolio, SiteSettings


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "author_name", "status", "views_count", "published_at")
    list_filter = ("category", "status", "published_at")
    search_fields = ("title", "summary", "content", "author_name")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(ProjectPortfolio)
class ProjectPortfolioAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "partner_or_client", "is_featured", "completion_date")
    list_filter = ("category", "is_featured")
    search_fields = ("title", "subtitle", "description", "technologies_used")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ("site_name", "contact_email", "emergency_line", "alert_banner_active", "alert_banner_level")
