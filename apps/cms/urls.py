from django.urls import path
from . import views

app_name = "cms"

urlpatterns = [
    # Public pages
    path("blog/", views.blog_list_view, name="blog_list"),
    path("blog/<slug:slug>/", views.blog_detail_view, name="blog_detail"),
    path("portfolio/", views.portfolio_list_view, name="portfolio_list"),
    # API endpoints for Dashboard CMS management
    path("api/cms/data/", views.api_cms_data, name="api_cms_data"),
    path("api/cms/posts/create/", views.api_post_create, name="api_post_create"),
    path("api/cms/posts/<int:pk>/update/", views.api_post_update, name="api_post_update"),
    path("api/cms/posts/<int:pk>/delete/", views.api_post_delete, name="api_post_delete"),
    path("api/cms/portfolio/create/", views.api_portfolio_create, name="api_portfolio_create"),
    path("api/cms/portfolio/<int:pk>/update/", views.api_portfolio_update, name="api_portfolio_update"),
    path("api/cms/portfolio/<int:pk>/delete/", views.api_portfolio_delete, name="api_portfolio_delete"),
    path("api/cms/settings/update/", views.api_settings_update, name="api_settings_update"),
]
