from django.urls import path

from . import views

app_name = "veiculos"

urlpatterns = [
    path("estoque/", views.estoque, name="estoque"),
    path("patio/", views.patio, name="patio"),
    path("carros/novo/", views.novo, name="novo"),
    path("carros/<int:pk>/", views.detalhe, name="detalhe"),
    path("carros/<int:pk>/editar/", views.editar, name="editar"),
    path("carros/<int:pk>/arquivar/", views.arquivar, name="arquivar"),
    path("carros/<int:pk>/documento/", views.adicionar_documento, name="adicionar_documento"),
    path("carros/<int:pk>/fotos/", views.adicionar_fotos, name="adicionar_fotos"),
    path("fotos/<int:foto_pk>/remover/", views.remover_foto_view, name="remover_foto"),
    path("fotos/<int:foto_pk>/capa/", views.definir_capa_view, name="definir_capa"),
]
