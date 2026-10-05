from django.urls import path

from . import views

app_name = "negocios"

urlpatterns = [
    path("negocios/novo/<str:tipo>/", views.iniciar, name="iniciar"),
    path("negocios/<int:pk>/", views.detalhe, name="detalhe"),
    path("negocios/<int:pk>/passo/quem/", views.passo_pessoa, name="passo_pessoa"),
    path("negocios/<int:pk>/passo/carro/", views.passo_carro, name="passo_carro"),
    path("negocios/<int:pk>/passo/pagamento/", views.passo_pagamento, name="passo_pagamento"),
    # Troca
    path("negocios/<int:pk>/troca/carro-loja/", views.troca_carro_loja, name="troca_carro_loja"),
    path(
        "negocios/<int:pk>/troca/carro-cliente/",
        views.troca_carro_cliente,
        name="troca_carro_cliente",
    ),
    path("negocios/<int:pk>/troca/valores/", views.troca_valores, name="troca_valores"),
    # Revisão / cancelamento
    path("negocios/<int:pk>/revisao/", views.revisao, name="revisao"),
    path(
        "negocios/<int:pk>/cancelar/",
        views.confirmar_cancelamento,
        name="confirmar_cancelamento",
    ),
    path("negocios/<int:pk>/cancelar/confirmar/", views.cancelar, name="cancelar"),
    # Consignação
    path("consignacoes/nova/", views.consignar, name="consignar"),
    path(
        "consignacoes/<int:consignacao_pk>/vender/",
        views.iniciar_consignado,
        name="iniciar_consignado",
    ),
    path(
        "consignacoes/<int:consignacao_pk>/repasse/",
        views.repasse,
        name="repasse",
    ),
    path(
        "consignacoes/<int:consignacao_pk>/devolver/",
        views.devolver,
        name="devolver",
    ),
    # Venda de consignado (passos próprios)
    path(
        "negocios/<int:pk>/consignado/comprador/",
        views.consignado_comprador,
        name="consignado_comprador",
    ),
    path(
        "negocios/<int:pk>/consignado/valores/",
        views.consignado_valores,
        name="consignado_valores",
    ),
]
