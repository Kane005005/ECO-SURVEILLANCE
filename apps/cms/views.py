import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import F, Q
from .models import BlogPost, ProjectPortfolio, SiteSettings


# ─────────────────────────────────────────────────────────────
# PUBLIC VIEWS
# ─────────────────────────────────────────────────────────────

def blog_list_view(request):
    """
    Public view: /blog/
    List published blog posts with category filtering and search.
    """
    category = request.GET.get("category", "").strip()
    search = request.GET.get("q", "").strip()

    posts = BlogPost.objects.filter(status="PUBLISHED")
    if category:
        posts = posts.filter(category=category)
    if search:
        posts = posts.filter(
            Q(title__icontains=search) | Q(summary__icontains=search) | Q(content__icontains=search)
        )

    categories = BlogPost.CATEGORY_CHOICES
    featured_post = posts.first()
    other_posts = posts[1:] if featured_post else []

    context = {
        "posts": posts,
        "featured_post": featured_post,
        "other_posts": other_posts,
        "categories": categories,
        "active_category": category,
        "search_query": search,
    }
    return render(request, "cms/blog_list.html", context)


def blog_detail_view(request, slug):
    """
    Public view: /blog/<slug>/
    Detail view of a blog post, increments views_count.
    """
    post = get_object_or_404(BlogPost, slug=slug)
    # Increment view count
    BlogPost.objects.filter(pk=post.pk).update(views_count=F("views_count") + 1)
    post.refresh_from_db()

    related_posts = BlogPost.objects.filter(
        category=post.category, status="PUBLISHED"
    ).exclude(pk=post.pk)[:3]

    context = {
        "post": post,
        "related_posts": related_posts,
    }
    return render(request, "cms/blog_detail.html", context)


def portfolio_list_view(request):
    """
    Public view: /portfolio/
    Showcase of ECO-SURVEILLANCE projects and environmental deployments.
    """
    category = request.GET.get("category", "").strip()
    projects = ProjectPortfolio.objects.all()
    if category:
        projects = projects.filter(category=category)

    categories = ProjectPortfolio.CATEGORY_CHOICES
    featured_projects = projects.filter(is_featured=True)

    context = {
        "projects": projects,
        "featured_projects": featured_projects,
        "categories": categories,
        "active_category": category,
    }
    return render(request, "cms/portfolio_list.html", context)


# ─────────────────────────────────────────────────────────────
# REST APIS FOR DASHBOARD MANAGEMENT
# ─────────────────────────────────────────────────────────────

def api_cms_data(request):
    """
    GET /api/cms/data/
    Returns full CMS data (posts, portfolio, settings) for Dashboard.
    """
    posts = list(BlogPost.objects.order_by("-created_at").values(
        "id", "title", "slug", "category", "summary", "author_name",
        "status", "views_count", "published_at", "created_at", "cover_image_url"
    ))
    # format dates
    for p in posts:
        if p["published_at"]:
            p["published_at_display"] = p["published_at"].strftime("%d/%m/%Y")
        p["created_at_display"] = p["created_at"].strftime("%d/%m/%Y")

    portfolio = list(ProjectPortfolio.objects.order_by("-created_at").values(
        "id", "title", "slug", "subtitle", "category", "partner_or_client",
        "technologies_used", "demo_url", "is_featured", "completion_date", "cover_image_url"
    ))
    for pr in portfolio:
        if pr["completion_date"]:
            pr["completion_date_display"] = pr["completion_date"].strftime("%d/%m/%Y")

    settings_obj = SiteSettings.get_settings()
    settings_dict = {
        "site_name": settings_obj.site_name,
        "site_tagline": settings_obj.site_tagline,
        "contact_email": settings_obj.contact_email,
        "contact_phone": settings_obj.contact_phone,
        "whatsapp_phone": settings_obj.whatsapp_phone,
        "emergency_line": settings_obj.emergency_line,
        "headquarters_address": settings_obj.headquarters_address,
        "facebook_url": settings_obj.facebook_url,
        "twitter_url": settings_obj.twitter_url,
        "linkedin_url": settings_obj.linkedin_url,
        "github_url": settings_obj.github_url,
        "alert_banner_active": settings_obj.alert_banner_active,
        "alert_banner_text": settings_obj.alert_banner_text,
        "alert_banner_level": settings_obj.alert_banner_level,
    }

    return JsonResponse({
        "status": "ok",
        "posts": posts,
        "portfolio": portfolio,
        "settings": settings_dict,
    })


@csrf_exempt
@require_http_methods(["POST"])
def api_post_create(request):
    """POST /api/cms/posts/create/"""
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except Exception:
        return JsonResponse({"status": "error", "message": "JSON invalide"}, status=400)

    title = (data.get("title") or "").strip()
    if not title:
        return JsonResponse({"status": "error", "message": "Le titre est obligatoire"}, status=400)

    post = BlogPost.objects.create(
        title=title,
        category=data.get("category", "NEWS"),
        summary=data.get("summary", ""),
        content=data.get("content", ""),
        author_name=data.get("author_name", "Équipe ECO-SURVEILLANCE") or "Équipe ECO-SURVEILLANCE",
        status=data.get("status", "PUBLISHED"),
        cover_image_url=data.get("cover_image_url", ""),
    )
    return JsonResponse({"status": "ok", "message": "Article créé avec succès", "post_id": post.id, "slug": post.slug}, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def api_post_update(request, pk):
    """POST /api/cms/posts/<pk>/update/"""
    post = get_object_or_404(BlogPost, pk=pk)
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except Exception:
        return JsonResponse({"status": "error", "message": "JSON invalide"}, status=400)

    if "title" in data and data["title"].strip():
        post.title = data["title"].strip()
    if "category" in data:
        post.category = data["category"]
    if "summary" in data:
        post.summary = data["summary"]
    if "content" in data:
        post.content = data["content"]
    if "author_name" in data:
        post.author_name = data["author_name"]
    if "status" in data:
        post.status = data["status"]
    if "cover_image_url" in data:
        post.cover_image_url = data["cover_image_url"]
    post.save()

    return JsonResponse({"status": "ok", "message": "Article mis à jour", "post_id": post.id})


@csrf_exempt
@require_http_methods(["POST"])
def api_post_delete(request, pk):
    """POST /api/cms/posts/<pk>/delete/"""
    post = get_object_or_404(BlogPost, pk=pk)
    post.delete()
    return JsonResponse({"status": "ok", "message": "Article supprimé"})


@csrf_exempt
@require_http_methods(["POST"])
def api_portfolio_create(request):
    """POST /api/cms/portfolio/create/"""
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except Exception:
        return JsonResponse({"status": "error", "message": "JSON invalide"}, status=400)

    title = (data.get("title") or "").strip()
    if not title:
        return JsonResponse({"status": "error", "message": "Le titre du projet est obligatoire"}, status=400)

    project = ProjectPortfolio.objects.create(
        title=title,
        subtitle=data.get("subtitle", ""),
        category=data.get("category", "SURVEILLANCE"),
        description=data.get("description", ""),
        partner_or_client=data.get("partner_or_client", ""),
        technologies_used=data.get("technologies_used", "Google Earth Engine, Sentinel-2, GloFAS"),
        demo_url=data.get("demo_url", ""),
        is_featured=bool(data.get("is_featured", False)),
        cover_image_url=data.get("cover_image_url", ""),
    )
    return JsonResponse({"status": "ok", "message": "Projet créé avec succès", "project_id": project.id, "slug": project.slug}, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def api_portfolio_update(request, pk):
    """POST /api/cms/portfolio/<pk>/update/"""
    project = get_object_or_404(ProjectPortfolio, pk=pk)
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except Exception:
        return JsonResponse({"status": "error", "message": "JSON invalide"}, status=400)

    if "title" in data and data["title"].strip():
        project.title = data["title"].strip()
    if "subtitle" in data:
        project.subtitle = data["subtitle"]
    if "category" in data:
        project.category = data["category"]
    if "description" in data:
        project.description = data["description"]
    if "partner_or_client" in data:
        project.partner_or_client = data["partner_or_client"]
    if "technologies_used" in data:
        project.technologies_used = data["technologies_used"]
    if "demo_url" in data:
        project.demo_url = data["demo_url"]
    if "is_featured" in data:
        project.is_featured = bool(data["is_featured"])
    if "cover_image_url" in data:
        project.cover_image_url = data["cover_image_url"]
    project.save()

    return JsonResponse({"status": "ok", "message": "Projet mis à jour", "project_id": project.id})


@csrf_exempt
@require_http_methods(["POST"])
def api_portfolio_delete(request, pk):
    """POST /api/cms/portfolio/<pk>/delete/"""
    project = get_object_or_404(ProjectPortfolio, pk=pk)
    project.delete()
    return JsonResponse({"status": "ok", "message": "Projet supprimé"})


@csrf_exempt
@require_http_methods(["POST"])
def api_settings_update(request):
    """POST /api/cms/settings/update/"""
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except Exception:
        return JsonResponse({"status": "error", "message": "JSON invalide"}, status=400)

    settings_obj = SiteSettings.get_settings()
    if "site_name" in data:
        settings_obj.site_name = data["site_name"].strip() or settings_obj.site_name
    if "site_tagline" in data:
        settings_obj.site_tagline = data["site_tagline"].strip()
    if "contact_email" in data:
        settings_obj.contact_email = data["contact_email"].strip()
    if "contact_phone" in data:
        settings_obj.contact_phone = data["contact_phone"].strip()
    if "whatsapp_phone" in data:
        settings_obj.whatsapp_phone = data["whatsapp_phone"].strip()
    if "emergency_line" in data:
        settings_obj.emergency_line = data["emergency_line"].strip()
    if "headquarters_address" in data:
        settings_obj.headquarters_address = data["headquarters_address"].strip()
    if "facebook_url" in data:
        settings_obj.facebook_url = data["facebook_url"].strip()
    if "twitter_url" in data:
        settings_obj.twitter_url = data["twitter_url"].strip()
    if "linkedin_url" in data:
        settings_obj.linkedin_url = data["linkedin_url"].strip()
    if "github_url" in data:
        settings_obj.github_url = data["github_url"].strip()
    if "alert_banner_active" in data:
        settings_obj.alert_banner_active = bool(data["alert_banner_active"])
    if "alert_banner_text" in data:
        settings_obj.alert_banner_text = data["alert_banner_text"].strip()
    if "alert_banner_level" in data:
        settings_obj.alert_banner_level = data["alert_banner_level"]
    settings_obj.save()

    return JsonResponse({"status": "ok", "message": "Paramètres du site enregistrés avec succès"})
