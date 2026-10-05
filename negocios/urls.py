from django.urls import path

from . import views

app_name = "negocios"

urlpatterns = [
    path("negocios/novo/<str:tipo>/", views.iniciar, name="iniciar"),
    path("negocios/<int:pk>/", views.detalhe, name="detalhe"),
    path("negocios/<int:pk>/passo/quem/", views.passo_pessoa, name="passo_pessoa"),
    path("negocios/<int:pk>/passo/carro/", views.passo_carro, name="passo_carro"),
    path("negocios/<int:pk>/passo/pagamento/", views.passo_pagamento, name="passo_pagamento"),
    path("negocios/<int:pk>/revisao/", views.revisao, name="revisao"),
    path(
        "negocios/<int:pk>/cancelar/", views.confirmar_cancelamento, name="confirmar_cancelamento"
    ),
    path("negocios/<int:pk>/cancelar/confirmar/", views.cancelar, name="cancelar"),
]
