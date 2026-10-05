from django.urls import path

from . import views

app_name = "pessoas"

urlpatterns = [
    path("pessoas/", views.lista, name="lista"),
    path("pessoas/nova/", views.novo, name="novo"),
    path("pessoas/nova-rapida/", views.novo_rapido, name="novo_rapido"),
    path("pessoas/<int:pk>/", views.detalhe, name="detalhe"),
    path("pessoas/<int:pk>/editar/", views.editar, name="editar"),
    path("pessoas/<int:pk>/arquivar/", views.arquivar, name="arquivar"),
]
