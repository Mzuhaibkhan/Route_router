"""URL configuration for Route Radar project."""

from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.urls import include, path, re_path


def serve_spa(request):
    index_file = settings.BASE_DIR.parent / "frontend" / "dist" / "index.html"
    if index_file.exists():
        return FileResponse(open(index_file, "rb"), content_type="text/html")
    msg = "<h1>Route Radar API</h1><p>Run 'npm run build' inside frontend/.</p>"
    return HttpResponse(msg, content_type="text/html", status=200)


def serve_sitemap(request):
    sitemap_file = settings.BASE_DIR.parent / "frontend" / "dist" / "sitemap.xml"
    if sitemap_file.exists():
        return FileResponse(open(sitemap_file, "rb"), content_type="application/xml")
    return HttpResponse(status=404)


def serve_robots(request):
    robots_file = settings.BASE_DIR.parent / "frontend" / "dist" / "robots.txt"
    if robots_file.exists():
        return FileResponse(open(robots_file, "rb"), content_type="text/plain")
    return HttpResponse(status=404)


urlpatterns = [
    path('healthz', lambda req: HttpResponse('OK', content_type='text/plain')),
    path("api/", include("api.urls")),
    path("sitemap.xml", serve_sitemap),
    path("robots.txt", serve_robots),
    re_path(r"^(?!api/).*$", serve_spa),
]
