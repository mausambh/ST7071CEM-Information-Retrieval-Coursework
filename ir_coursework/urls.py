from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Main coursework dashboard.
    path("", include("core.urls")),
    # Vertical search engine interface.
    path(
        "search/",
        include("search_engine.urls"),
    ),
    # Document clustering interface.
    path(
        "clustering/",
        include("clustering.urls"),
    ),
]
