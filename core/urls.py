from django.urls import path

from . import views


# Giving the app its own URL namespace keeps route names organised
# as the coursework grows to include search and clustering pages.
app_name = "core"


urlpatterns = [
    # The root page of the website will display the main dashboard.
    path(
        "",
        views.home,
        name="home",
    ),
]