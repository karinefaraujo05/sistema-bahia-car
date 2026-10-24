"""
Cadastra/atualiza os veículos a partir das FOTOS DOS DOCUMENTOS (CRLV-e/ATPV-e)
que estão na loja. Lê o JSON gerado a partir das fotos (~/Downloads/estoque/
_dados_documentos.json) e, para cada carro:

  - acha o veículo que já existe na Bahia Car (por renavam OU placa) e completa
    com os dados do documento (chassi, renavam certo, cor, ano, dono registral);
  - se não existir (carro sem contrato), cria;
  - define a situação final: "na loja" (estoque) ou "vendido", conforme a
    conferência feita com a Karine.

Uso:
    python manage.py importar_estoque --dry-run
    python manage.py importar_estoque
"""

import json
import os
import re

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from contas.models import Empresa, Usuario
from core.tenancy import limpar_empresa_atual, set_empresa_atual
from veiculos.models import Cambio, Combustivel, Situacao, StatusVeiculo, Veiculo
from veiculos.validators import normalizar_placa

JSON_PADRAO = os.path.expanduser("~/Downloads/estoque/_dados_documentos.json")
EMPRESA_NOME = "Bahia Car"
USUARIO_LOGIN = "nelson"
MARCA_DOC = "[DADOS DO DOCUMENTO (CRLV/ATPV)]"

COMBUSTIVEIS = {c.value for c in Combustivel}


def limpar_chassi(ch):
    ch = re.sub(r"[^A-Za-z0-9]", "", ch or "").upper()
    return ch[:17]


def so_digitos(s):
    return re.sub(r"\D", "", s or "")


class Command(BaseCommand):
    help = "Cadastra/atualiza veículos a partir dos documentos fotografados."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--json", default=JSON_PADRAO)

    def handle(self, *args, **opts):
        dados = json.load(open(opts["json"], encoding="utf-8"))["veiculos"]
        dry = opts["dry_run"]
        self.stdout.write(self.style.WARNING(
            f"\n{'='*70}\n{'MODO TESTE (nada gravado)' if dry else 'GRAVANDO'} — "
            f"{len(dados)} veículos de documento\n{'='*70}"))

        empresa = Empresa.objects.get(nome=EMPRESA_NOME)
        usuario = Usuario.objects.get(username=USUARIO_LOGIN)
        set_empresa_atual(empresa)
        criados = atualizados = 0
        try:
            for d in dados:
                placa = normalizar_placa(d.get("placa", ""))
                renav = so_digitos(d.get("renavam", ""))
                renav = renav if len(renav) == 11 else ""
                vendido = d.get("situacao") == "vendido"

                existente = None
                cond = Q()
                if placa:
                    cond |= Q(placa=placa)
                if renav:
                    cond |= Q(renavam=renav)
                if cond:
                    existente = Veiculo.objetos.filter(cond).first()

                acao = "ATUALIZA" if existente else "CRIA"
                sit = "VENDIDO" if vendido else "na loja"
                self.stdout.write(self.style.HTTP_INFO(
                    f"\n[{acao}] {d['marca']} {d['modelo']} — placa {placa} "
                    f"renavam {renav or '—'} → {sit}"))
                self.stdout.write(
                    f"   chassi {d.get('chassi','—')} | cor {d.get('cor','—')} | "
                    f"ano {d.get('ano_fab','?')}/{d.get('ano_mod','?')} | "
                    f"dono doc: {d.get('proprietario_doc','—')}")
                if existente:
                    self.stdout.write(f"   (casou com veículo id={existente.id} já no sistema)")

                if dry:
                    continue
                with transaction.atomic():
                    if existente:
                        self._atualizar(existente, d, usuario, vendido)
                        atualizados += 1
                        self.stdout.write(self.style.SUCCESS("   → atualizado"))
                    else:
                        self._criar(d, usuario, vendido)
                        criados += 1
                        self.stdout.write(self.style.SUCCESS("   → criado"))
        finally:
            limpar_empresa_atual()

        self.stdout.write(self.style.WARNING(f"\n{'='*70}"))
        if dry:
            self.stdout.write("Modo teste. Rode sem --dry-run para gravar.")
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Pronto: {criados} criados, {atualizados} atualizados."))

    def _campos_doc(self, d):
        comb = (d.get("combustivel") or "").lower()
        nota = (f"{MARCA_DOC} doc: {d.get('arquivo','')} | "
                f"dono no documento: {d.get('proprietario_doc','')} "
                f"CPF {d.get('cpf_doc','')}")
        if d.get("contrato"):
            nota += f" | contrato: {d['contrato']}"
        if d.get("obs"):
            nota += f" | {d['obs']}"
        campos = dict(
            renavam=so_digitos(d.get("renavam", ""))[:11],
            chassi=limpar_chassi(d.get("chassi", "")),
            cor=(d.get("cor", "") or "")[:40],
            combustivel=comb if comb in COMBUSTIVEIS else "",
            proprietario_registral=(d.get("proprietario_doc", "") or "")[:120],
        )
        return campos, nota

    def _atualizar(self, v, d, usuario, vendido):
        campos, nota = self._campos_doc(d)
        for k, val in campos.items():
            if val:  # não apaga o que já tem se o doc vier vazio
                setattr(v, k, val)
        # placa do documento é a oficial (corrige OCR torto do contrato)
        placa_doc = normalizar_placa(d.get("placa", ""))
        if placa_doc:
            v.placa = placa_doc
        if not v.ano_fabricacao and d.get("ano_fab"):
            v.ano_fabricacao = d["ano_fab"]
            v.ano_modelo = d.get("ano_mod") or d["ano_fab"]
        v.status = StatusVeiculo.VENDIDO if vendido else StatusVeiculo.EM_ESTOQUE
        v.situacao = Situacao.PROPRIO
        if MARCA_DOC not in (v.observacoes or ""):
            v.observacoes = f"{(v.observacoes or '').strip()}\n{nota}".strip()
        v.atualizado_por = usuario
        v.save()

    def _criar(self, d, usuario, vendido):
        campos, nota = self._campos_doc(d)
        Veiculo.objetos.create(
            placa=normalizar_placa(d.get("placa", "")),
            marca=(d.get("marca", "") or "")[:60],
            modelo=(d.get("modelo", "") or "")[:120],
            ano_fabricacao=d.get("ano_fab") or 0,
            ano_modelo=d.get("ano_mod") or d.get("ano_fab") or 0,
            cambio=Cambio.MANUAL,
            situacao=Situacao.PROPRIO,
            status=StatusVeiculo.VENDIDO if vendido else StatusVeiculo.EM_ESTOQUE,
            observacoes=nota,
            criado_por=usuario,
            **campos,
        )
