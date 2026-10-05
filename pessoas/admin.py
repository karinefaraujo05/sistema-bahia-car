from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Pessoa


@admin.register(Pessoa)
class PessoaAdmin(SimpleHistoryAdmin):
    list_display = ("nome", "tipo", "cpf_cnpj", "telefone", "arquivado")
    list_filter = ("tipo", "arquivado")
    search_fields = ("nome", "cpf_cnpj", "telefone")

    def get_queryset(self, request):
        return self.model.todos.all()
