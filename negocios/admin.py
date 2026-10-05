from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Consignacao, ItemNegocio, Negocio, ParteNegocio


class ParteNegocioInline(admin.TabularInline):
    model = ParteNegocio
    extra = 0


class ItemNegocioInline(admin.TabularInline):
    model = ItemNegocio
    extra = 0


@admin.register(Negocio)
class NegocioAdmin(SimpleHistoryAdmin):
    list_display = ("numero_contrato", "tipo", "modalidade", "data", "valor_total", "status")
    list_filter = ("tipo", "modalidade", "status")
    inlines = [ParteNegocioInline, ItemNegocioInline]

    def get_queryset(self, request):
        return self.model.todos.all()


@admin.register(Consignacao)
class ConsignacaoAdmin(SimpleHistoryAdmin):
    list_display = ("numero_contrato", "veiculo", "proprietario", "status", "repasse_feito_em")
    list_filter = ("status", "comissao_tipo")

    def get_queryset(self, request):
        return self.model.todos.all()
