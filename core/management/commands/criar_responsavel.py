"""
Cria a empresa e o usuário responsável (o dono da loja) a partir de variáveis
de ambiente. Feito pra rodar na publicação (Render), onde não há terminal no
plano grátis. É idempotente: pode rodar toda vez que o site sobe sem duplicar nada.

Variáveis lidas do ambiente:
  RESP_USUARIO       login (ex.: nelson). Se vazio, o comando não faz nada.
  RESP_SENHA         senha (só é aplicada ao criar, ou se RESP_RESET_SENHA=1).
  RESP_NOME          nome que aparece no topo (ex.: Nelson).
  RESP_EMPRESA       nome da empresa/loja (padrão: "Bahia Car").
  RESP_RESET_SENHA   se "1", redefine a senha mesmo que o usuário já exista.
"""

import os

from django.core.management.base import BaseCommand

from contas.models import Empresa, Usuario
from core.tenancy import limpar_empresa_atual, set_empresa_atual


class Command(BaseCommand):
    help = "Cria a loja e o usuário dono a partir de variáveis de ambiente (RESP_*)."

    def handle(self, *args, **options):
        usuario = (os.environ.get("RESP_USUARIO") or "").strip()
        if not usuario:
            self.stdout.write("RESP_USUARIO não definido — nada a fazer.")
            return

        senha = os.environ.get("RESP_SENHA") or ""
        nome = (os.environ.get("RESP_NOME") or usuario).strip()
        nome_empresa = (os.environ.get("RESP_EMPRESA") or "Bahia Car").strip()
        resetar = os.environ.get("RESP_RESET_SENHA") == "1"

        empresa, _ = Empresa.objects.get_or_create(nome=nome_empresa)

        user, criado = Usuario.objects.get_or_create(
            username=usuario,
            defaults={"papel": Usuario.Papel.ADMINISTRADOR},
        )
        user.papel = Usuario.Papel.ADMINISTRADOR
        user.empresa = empresa
        user.is_superuser = True  # dono: pode fazer tudo (arquivar, backup…)
        user.is_staff = True
        user.first_name = nome
        if criado or resetar:
            if not senha:
                self.stderr.write("RESP_SENHA vazia: defina a senha no painel.")
                return
            user.set_password(senha)
        user.save()

        # Garante que exista uma Configuração da Loja pra essa empresa.
        set_empresa_atual(empresa)
        try:
            from contratos.models import ConfiguracaoLoja

            ConfiguracaoLoja.carregar(empresa=empresa)
        finally:
            limpar_empresa_atual()

        acao = "criado" if criado else "atualizado"
        self.stdout.write(
            self.style.SUCCESS(f"Responsável {acao}: {usuario} (loja: {nome_empresa}).")
        )
