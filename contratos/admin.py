from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import ConfiguracaoLoja, Contrato, Documento


@admin.register(ConfiguracaoLoja)
class ConfiguracaoLojaAdmin(SimpleHistoryAdmin):
    def get_queryset(self, request):
        return self.model.todos.all()


@admin.register(Contrato)
class ContratoAdmin(SimpleHistoryAdmin):
    list_display = ("titulo", "modelo", "versao", "negocio", "consignacao", "criado_em")
    list_filter = ("modelo",)

    def get_queryset(self, request):
        return self.model.todos.all()


@admin.register(Documento)
class DocumentoAdmin(SimpleHistoryAdmin):
    list_display = ("tipo", "negocio", "consignacao", "gerado_pelo_sistema", "criado_em")
    list_filter = ("tipo", "gerado_pelo_sistema")

    def get_queryset(self, request):
        return self.model.todos.all()
