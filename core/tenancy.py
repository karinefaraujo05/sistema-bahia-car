"""
"Empresa atual" da requisição (multi-empresa).

Cada usuário pertence a uma empresa. Um middleware guarda aqui a empresa do
usuário logado durante a requisição; o gerenciador padrão (`objetos`) filtra
automaticamente por ela. Fora de uma requisição (migrações, shell, testes sem
login), fica None e nada é filtrado.
"""

import contextvars

_empresa_atual = contextvars.ContextVar("empresa_atual", default=None)


def set_empresa_atual(empresa):
    _empresa_atual.set(empresa)


def empresa_atual():
    return _empresa_atual.get()


def limpar_empresa_atual():
    _empresa_atual.set(None)
