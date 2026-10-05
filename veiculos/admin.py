from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import FotoVeiculo, Veiculo


class FotoVeiculoInline(admin.TabularInline):
    model = FotoVeiculo
    extra = 0
    fields = ("imagem", "ordem", "capa", "arquivado")


@admin.register(Veiculo)
class VeiculoAdmin(SimpleHistoryAdmin):
    list_display = ("placa", "marca", "modelo", "situacao", "status", "arquivado")
    list_filter = ("situacao", "status", "arquivado")
    search_fields = ("placa", "marca", "modelo")
    inlines = [FotoVeiculoInline]

    def get_queryset(self, request):
        # No painel, o superusuário vê tudo, inclusive arquivados.
        return self.model.todos.all()
