from django.urls import path
from . import views


urlpatterns = [
    path("process/<int:pk>/", views.process_xml_pk, name="process_xml_pk"),
    path(
        "revalidate-sps/<int:pk>/",
        views.revalidate_sps_package_pk,
        name="revalidate_sps_package_pk",
    ),
]
