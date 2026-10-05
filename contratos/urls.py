from django.urls import path

from . import views

app_name = "contratos"

urlpatterns = [
    path("configuracao/", views.configuracao, name="configuracao"),
    path(
        "negocios/<int:negocio_pk>/documentos/",
        views.upload_documentos,
        name="upload_documentos",
    ),
]
