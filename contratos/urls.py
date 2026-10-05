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
    path("negocios/<int:negocio_pk>/contrato/gerar/", views.gerar, name="gerar"),
    path("negocios/<int:negocio_pk>/vistoria/gerar/", views.gerar_termo, name="gerar_termo"),
    path(
        "consignacoes/<int:consignacao_pk>/contrato/gerar/",
        views.gerar_consignacao,
        name="gerar_consignacao",
    ),
    path("contratos/<int:pk>/editar/", views.editar_contrato, name="editar_contrato"),
    path("contratos/<int:pk>/pdf/", views.baixar_pdf, name="baixar_pdf"),
    path("contratos/<int:pk>/docx/", views.baixar_docx, name="baixar_docx"),
]
