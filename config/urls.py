"""Rotas do projeto. O admin fica em URL não óbvia (ver settings ADMIN_URL)."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from core.views import ajuda, buscar, inicio

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("conta/", include("contas.urls")),
    path("", include("veiculos.urls")),
    path("", include("pessoas.urls")),
    path("", include("negocios.urls")),
    path("", include("contratos.urls")),
    path("buscar/", buscar, name="buscar"),
    path("ajuda/", ajuda, name="ajuda"),
    path("", inicio, name="inicio"),
]

# Em desenvolvimento, o Django serve os arquivos de mídia enviados.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
