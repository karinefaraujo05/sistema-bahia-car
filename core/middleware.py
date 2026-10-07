"""Middleware que define a empresa atual a partir do usuário logado."""

from .tenancy import limpar_empresa_atual, set_empresa_atual


class EmpresaAtualMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        empresa = None
        if user is not None and user.is_authenticated:
            empresa = getattr(user, "empresa", None)
        set_empresa_atual(empresa)
        try:
            return self.get_response(request)
        finally:
            limpar_empresa_atual()
