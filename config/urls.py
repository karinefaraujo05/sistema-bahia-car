"""Rotas do projeto. O admin fica em URL não óbvia (ver settings ADMIN_URL)."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from core.views import (
    agenda,
    ajuda,
    baixar_backup,
    buscar,
    consulta,
    consulta_fipe,
    inicio,
    manifest,
    service_worker,
)

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("conta/", include("contas.urls")),
    path("", include("veiculos.urls")),
    path("", include("pessoas.urls")),
    path("", include("negocios.urls")),
    path("", include("contratos.urls")),
    path("buscar/", buscar, name="buscar"),
    path("ajuda/", ajuda, name="ajuda"),
    path("agenda/", agenda, name="agenda"),
    path("consulta/", consulta, name="consulta"),
    path("fipe/", consulta_fipe, name="fipe"),
    path("backup/", baixar_backup, name="backup"),
    path("manifest.webmanifest", manifest, name="manifest"),
    path("sw.js", service_worker, name="service_worker"),
    path("", inicio, name="inicio"),
]

# Em desenvolvimento, o Django serve os arquivos de mídia enviados.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
