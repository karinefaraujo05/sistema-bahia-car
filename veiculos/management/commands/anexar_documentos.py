"""
Anexa as FOTOS DOS DOCUMENTOS (CRLV-e/ATPV-e) de cada carro ao veículo
correspondente no sistema, como Documento do tipo "Documento do veículo".

Lê o mapa ~/Downloads/estoque/_dados_documentos.json (campo "arquivo" com o nome
curto da foto; carros com 2 fotos vêm separados por " / "). Casa o veículo por
renavam OU placa.

Rode com as settings que apontam o armazenamento pro R2:

    python manage.py anexar_documentos --dry-run --settings=config.settings.anexar_r2
    python manage.py anexar_documentos --settings=config.settings.anexar_r2

Idempotente: se o carro já tem aquela foto (pela descrição), pula.
"""

import json
import os
import re

from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from contas.models import Empresa, Usuario
from contratos.models import Documento, TipoDocumento
from core.tenancy import limpar_empresa_atual, set_empresa_atual
from veiculos.models import Veiculo
from veiculos.validators import normalizar_placa

PASTA_FOTOS = os.path.expanduser("~/Downloads/estoque")
JSON_PADRAO = os.path.join(PASTA_FOTOS, "_dados_documentos.json")
PREFIXO = "WhatsApp Image 2026-10-24 at "
EMPRESA_NOME = "Bahia Car"
USUARIO_LOGIN = "nelson"


def so_digitos(s):
    return re.sub(r"\D", "", s or "")


class Command(BaseCommand):
    help = "Anexa as fotos dos documentos (CRLV) aos veículos."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--json", default=JSON_PADRAO)
        parser.add_argument("--fotos", default=PASTA_FOTOS)

    def _caminho(self, pasta, curto):
        """Acha o arquivo da foto a partir do nome curto do JSON."""
        for nome in (PREFIXO + curto, curto):
            p = os.path.join(pasta, nome)
            if os.path.isfile(p):
                return p
        return None

    def handle(self, *args, **opts):
        dados = json.load(open(opts["json"], encoding="utf-8"))["veiculos"]
        pasta = opts["fotos"]
        dry = opts["dry_run"]
        empresa = Empresa.objects.get(nome=EMPRESA_NOME)
        usuario = Usuario.objects.get(username=USUARIO_LOGIN)
        set_empresa_atual(empresa)
        self.stdout.write(self.style.WARNING(
            f"\n{'MODO TESTE' if dry else 'ANEXANDO FOTOS'} — {len(dados)} carros\n"))
        anexadas = puladas = sem_carro = sem_foto = 0
        try:
            for d in dados:
                placa = normalizar_placa(d.get("placa", ""))
                renav = so_digitos(d.get("renavam", ""))
                renav = renav if len(renav) == 11 else ""
                cond = Q()
                if placa:
                    cond |= Q(placa=placa)
                if renav:
                    cond |= Q(renavam=renav)
                veic = Veiculo.objetos.filter(cond).first() if cond else None
                rotulo = f"{d.get('marca','')} {d.get('modelo','')} ({placa})"
                if not veic:
                    sem_carro += 1
                    self.stdout.write(self.style.ERROR(f"  {rotulo}: carro não achado"))
                    continue
                for curto in [p.strip() for p in str(d.get("arquivo", "")).split("/") if p.strip()]:
                    caminho = self._caminho(pasta, curto)
                    if not caminho:
                        sem_foto += 1
                        self.stdout.write(self.style.ERROR(f"  {rotulo}: foto não achada «{curto}»"))
                        continue
                    nome_foto = os.path.basename(caminho)
                    if veic.documentos.filter(tipo=TipoDocumento.DOC_VEICULO,
                                              descricao=nome_foto).exists():
                        puladas += 1
                        self.stdout.write(f"  {rotulo}: já tem «{curto}», pulei")
                        continue
                    self.stdout.write(self.style.HTTP_INFO(f"  {rotulo} ← {curto}"))
                    if dry:
                        continue
                    with transaction.atomic():
                        with open(caminho, "rb") as fh:
                            doc = Documento(
                                veiculo=veic,
                                tipo=TipoDocumento.DOC_VEICULO,
                                descricao=nome_foto,
                                criado_por=usuario,
                                empresa=empresa,
                            )
                            doc.arquivo.save(nome_foto, File(fh), save=True)
                    anexadas += 1
                    self.stdout.write(self.style.SUCCESS("     → anexada"))
        finally:
            limpar_empresa_atual()

        self.stdout.write(self.style.WARNING(
            f"\nResumo: {anexadas} fotos anexadas, {puladas} já existiam, "
            f"{sem_carro} carros não achados, {sem_foto} fotos não achadas."))
