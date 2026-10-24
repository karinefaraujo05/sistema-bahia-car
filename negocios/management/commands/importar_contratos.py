"""
Importa os contratos ANTIGOS (feitos à mão, fora do sistema) da Bahia Car para
dentro do sistema, preservando o NÚMERO ORIGINAL do contrato.

Lê os .txt gerados a partir dos .docx e cria, na empresa do nelson:
  - a pessoa (cliente) do contrato;
  - o(s) veículo(s);
  - o negócio (venda/compra/troca) JÁ CONCLUÍDO, com o número original e o
    texto completo das observações.

Não usa `services.concluir_negocio` de propósito: aquele fluxo RENUMERA o
contrato automaticamente. Aqui a gente grava direto, preservando o número.

Uso:
    python manage.py importar_contratos --dry-run          # só mostra, não grava
    python manage.py importar_contratos                    # grava de verdade
    python manage.py importar_contratos --numeros 1071 1073 1131   # só esses
    python manage.py importar_contratos --limit 3          # só os 3 primeiros

É idempotente: cada negócio importado leva uma marca nas observações. Rodar de
novo pula o que já foi importado (não duplica).
"""

import datetime
import os
import re
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from contas.models import Empresa, Usuario
from core.tenancy import limpar_empresa_atual, set_empresa_atual
from negocios.models import (
    ItemNegocio,
    Modalidade,
    Negocio,
    PapelParte,
    ParteNegocio,
    StatusNegocio,
    TipoNegocio,
)
from pessoas.models import Pessoa, TipoPessoa
from veiculos.models import Cambio, Situacao, StatusVeiculo, Veiculo
from veiculos.validators import normalizar_placa

PASTA_PADRAO = os.path.expanduser("~/Downloads/Contratos-Nelson-leitura")
EMPRESA_NOME = "Bahia Car"
USUARIO_LOGIN = "nelson"
MARCA_IMPORT = "[IMPORTADO DO CONTRATO ANTIGO]"

MESES = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "março": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9,
    "outubro": 10, "novembro": 11, "dezembro": 12,
}

# Marca inferida a partir do nome do modelo (o contrato quase nunca traz a marca).
MODELO_PARA_MARCA = {
    "Fiat": ["PALIO", "UNO", "SIENA", "STRADA", "TORO", "PULSE", "ARGO", "MOBI",
             "CRONOS", "FIORINO", "DOBLO", "IDEA", "PUNTO", "LINEA", "BRAVO",
             "FREEMONT", "500", "WEEKEND"],
    "Volkswagen": ["GOL", "VOYAGE", "VOIAGE", "SAVEIRO", "FOX", "CROSSFOX",
                   "POLO", "VIRTUS", "T-CROSS", "TCROSS", "NIVUS", "JETTA",
                   "PASSAT", "AMAROK", "UP", "GOLF", "TIGUAN", "FUSCA", "KOMBI",
                   "SPACEFOX", "PARATI"],
    "Chevrolet": ["ONIX", "PRISMA", "CELTA", "CORSA", "CLASSIC", "COBALT",
                  "SPIN", "TRACKER", "CRUZE", "S10", "S 10", "MONTANA", "ASTRA",
                  "VECTRA", "ZAFIRA", "MERIVA", "CAPTIVA", "SONIC", "AGILE",
                  "BLAZER", "CAMARO", "OMEGA"],
    "Toyota": ["COROLLA", "HILUX", "ETIOS", "YARIS", "RAV4", "SW4", "CAMRY"],
    "Hyundai": ["HB20", "HB20S", "CRETA", "TUCSON", "IX35", "I30", "SANTA FE",
                "AZERA", "ELANTRA", "VELOSTER"],
    "Honda": ["CIVIC", "FIT", "CITY", "HR-V", "HRV", "WR-V", "WRV", "CR-V",
              "CRV", "ACCORD", "TWISTER", "BROS", "BROSS", "BIZ", "CG", "FAN",
              "TITAN", "XRE", "PCX", "CB"],
    "Ford": ["KA", "FIESTA", "FOCUS", "ECOSPORT", "ECO", "RANGER", "FUSION",
             "EDGE"],
    "Renault": ["KWID", "SANDERO", "SANDEIRO", "LOGAN", "DUSTER", "CAPTUR",
                "OROCH", "CLIO", "MEGANE", "FLUENCE", "STEPWAY"],
    "Nissan": ["KICKS", "VERSA", "MARCH", "SENTRA", "FRONTIER", "TIIDA",
               "LIVINA"],
    "Mitsubishi": ["L200", "L 200", "PAJERO", "PAJEIRO", "TRITON", "ASX",
                   "LANCER", "OUTLANDER", "ECLIPSE"],
    "Jeep": ["RENEGADE", "COMPASS", "COMMANDER", "WRANGLER"],
    "Peugeot": ["PEUGEOT", "208", "207", "206", "307", "2008", "3008", "408"],
    "Audi": ["AUDI", "Q5", "Q3", "A3", "A4"],
    "Yamaha": ["FAZER", "FACTOR", "YBR", "CROSSER"],
}

_PLACA_RE = re.compile(r"[A-Z]{3}[\s-]?[0-9][A-Z0-9][0-9]{2}", re.I)
_ANO_RE = re.compile(r"(\d{4})\s*/\s*(\d{2,4})")
_MONEY_RE = re.compile(r"R?\$?\s*([\d]{1,3}(?:\.\d{3})*(?:\.\d{2})?|\d+)", re.I)


def inferir_marca(modelo_texto):
    up = f" {modelo_texto.upper()} "
    for marca, chaves in MODELO_PARA_MARCA.items():
        for chave in chaves:
            if f" {chave} " in up or up.strip().startswith(chave):
                return marca
    return ""


def parse_dinheiro(texto):
    """'R$31.000.00' -> Decimal('31000.00'); '12.000' -> 12000; '100.00' -> 100."""
    t = texto.replace("R$", "").replace("r$", "").strip()
    grupos = re.split(r"[^\d]", t)
    grupos = [g for g in grupos if g != ""]
    if not grupos:
        return None
    if len(grupos) >= 2 and len(grupos[-1]) == 2:
        centavos = grupos[-1]
        inteiro = "".join(grupos[:-1])
    else:
        centavos = "00"
        inteiro = "".join(grupos)
    if not inteiro:
        inteiro = "0"
    try:
        return Decimal(f"{int(inteiro)}.{centavos}")
    except Exception:
        return None


def todos_valores(texto):
    vals = []
    for m in re.finditer(r"R\$ ?[\d.]+", texto):
        v = parse_dinheiro(m.group(0))
        if v is not None and v > 0:
            vals.append(v)
    return vals


def primeiro(texto, *rotulos):
    """Pega o que vem depois de um rótulo (NOME:, CPF:, ...) na mesma linha."""
    for linha in texto.splitlines():
        for rot in rotulos:
            m = re.search(rot + r"\s*[:;.\-]?\s*(.+)", linha, re.I)
            if m:
                val = m.group(1).strip(" .:;-\t")
                if val:
                    return val
    return ""


def so_digitos(s):
    return re.sub(r"\D", "", s or "")


def _parece_ano(tail4):
    return tail4.isdigit() and 1990 <= int(tail4) <= 2035


def tirar_placas(texto):
    """Remove tokens de placa do texto, MAS preserva '<modelo> <ano>' (ex.: PALIO 2013)."""
    def repl(m):
        cand = normalizar_placa(m.group(0))
        return m.group(0) if _parece_ano(cand[3:]) else " "
    return _PLACA_RE.sub(repl, texto)


def achar_placa(texto):
    # 1) logo depois da palavra PLACA (o caso mais confiável).
    m = re.search(r"PLACA\s*[:\-]?\s*([A-Z]{3}[\s-]?[0-9][A-Z0-9][0-9]{2})",
                  texto, re.I)
    if m:
        return normalizar_placa(m.group(1))
    # 2) qualquer candidato que NÃO pareça "<modelo> <ano>" (ex.: ASTRA 2005).
    for m in _PLACA_RE.finditer(texto):
        cand = normalizar_placa(m.group(0))
        if _parece_ano(cand[3:]):
            continue
        return cand
    return ""


def achar_renavam(texto):
    m = re.search(r"\b(\d{11})\b", texto)
    return m.group(1) if m else ""


def achar_ano(texto):
    m = _ANO_RE.search(texto)
    if m:
        fab = int(m.group(1))
        mod_raw = m.group(2)
        mod = int(str(fab)[:2] + mod_raw) if len(mod_raw) == 2 else int(mod_raw)
        return fab, mod
    # Contrato antigo às vezes traz só o ano cheio, sem "/YY".
    for m in re.finditer(r"\b(19|20)\d{2}\b", texto):
        y = int(m.group(0))
        if 1990 <= y <= 2035:
            return y, y
    return None, None


def parse_data(texto):
    # "07 Janeiro de 2026" / "07 de Janeiro de 2026"
    m = re.search(r"(\d{1,2})\s*(?:de\s*)?([A-Za-zçÇ]+)\s*(?:de\s*)?(\d{4})", texto)
    if m:
        mes = MESES.get(m.group(2).lower())
        if mes:
            try:
                return datetime.date(int(m.group(3)), mes, int(m.group(1)))
            except ValueError:
                return None
    # "23 / Setembro / 2026" ou "30/01/2026"
    m = re.search(r"(\d{1,2})\s*/\s*([A-Za-zçÇ]+|\d{1,2})\s*/\s*(\d{4})", texto)
    if m:
        g2 = m.group(2)
        mes = MESES.get(g2.lower()) if not g2.isdigit() else int(g2)
        if mes and 1 <= mes <= 12:
            try:
                return datetime.date(int(m.group(3)), mes, int(m.group(1)))
            except ValueError:
                return None
    return None


def forma_pagamento(obs):
    o = obs.lower()
    if "financ" in o:
        return "financiado"
    if "cart" in o:
        return "cartao"
    if "troca" in o and ("volta" in o or "diferenc" in o or "diferença" in o):
        return "troca_dinheiro"
    if "pix" in o or "transferenc" in o:
        return "pix"
    if "dinheiro" in o or "espécie" in o or "especie" in o:
        return "dinheiro"
    return ""


class Contrato:
    """Resultado de ler um .txt: dados extraídos + avisos do que ficou duvidoso."""

    def __init__(self, numero, arquivo):
        self.numero = numero
        self.arquivo = arquivo
        self.tipo = ""
        self.pessoa = {}
        self.carro = {}          # carro do bloco DADOS DO VEÍCULO
        self.carro_recebido = {} # 2º carro da troca (quando dá pra ler)
        self.valor = None
        self.diferenca = None
        self.data = None
        self.forma = ""
        self.obs = ""
        self.avisos = []


def ler_contrato(caminho):
    nome = os.path.basename(caminho)[:-4]
    texto = open(caminho, encoding="utf-8", errors="ignore").read()

    mnum = re.match(r"\s*(\d+)", nome)
    numero = int(mnum.group(1)) if mnum else None
    c = Contrato(numero, nome)

    up = texto.upper()
    # Tipo: pelo nome do arquivo, conferindo com o corpo.
    if "COMPRA" in nome.upper() or re.search(r"COMPRADOR\s*:\s*NELSON", up):
        c.tipo = TipoNegocio.COMPRA
    elif "TROCA" in nome.upper():
        c.tipo = TipoNegocio.TROCA
    elif "VENDA" in nome.upper():
        c.tipo = TipoNegocio.VENDA
    else:
        c.tipo = TipoNegocio.VENDA
        c.avisos.append("tipo não identificado pelo nome; assumi VENDA")

    # Bloco da contraparte: entre "DADOS DO COMPRADOR/VENDEDOR" e "DADOS DO VEÍCULO".
    mbloco = re.search(
        r"DADOS DO (?:COMPRADOR|VENDEDOR).*?(?=DADOS DO VE[IÍ]CULO)",
        texto, re.I | re.S,
    )
    bloco_pessoa = mbloco.group(0) if mbloco else texto
    c.pessoa = {
        "nome": primeiro(bloco_pessoa, "NOME"),
        "cpf": so_digitos(primeiro(bloco_pessoa, "CPF")),
        "rg": primeiro(bloco_pessoa, r"R\.?G"),
        "endereco": primeiro(bloco_pessoa, "ENDERE[ÇC]O"),
        "telefone": so_digitos(primeiro(bloco_pessoa, "TELEFONE"))[:11],
    }
    if not c.pessoa["nome"]:
        c.avisos.append("NÃO achei o nome da pessoa")
    if c.pessoa["cpf"] and len(c.pessoa["cpf"]) != 11:
        c.avisos.append(f"CPF com {len(c.pessoa['cpf'])} dígitos (confira)")

    # Bloco do veículo: de "DADOS DO VEÍCULO" até "OBSERVAÇÕES".
    mv = re.search(
        r"DADOS DO VE[IÍ]CULO(.*?)(?=OBSERVA|$)", texto, re.I | re.S
    )
    bloco_veic = mv.group(1) if mv else ""
    renav = achar_renavam(bloco_veic)
    bloco_sem_renav = bloco_veic.replace(renav, " ") if renav else bloco_veic
    placa = achar_placa(bloco_sem_renav)
    marca_modelo = primeiro(bloco_veic, "MARCA E MODELO", "MARCA/MODELO", "MARCA")
    tem_ano_na_linha = bool(_ANO_RE.search(marca_modelo)
                            or re.search(r"\b(19|20)\d{2}\b", marca_modelo))
    fab, mod = achar_ano(marca_modelo if tem_ano_na_linha else bloco_sem_renav)
    modelo_limpo = _ANO_RE.sub(" ", marca_modelo)
    modelo_limpo = re.sub(r"\b(19|20)\d{2}\b", " ", modelo_limpo)
    modelo_limpo = tirar_placas(modelo_limpo)
    modelo_limpo = re.sub(r"\b(PLACA|RENAVAM?|COR|CATEGORIA)\b", " ", modelo_limpo, flags=re.I)
    modelo_limpo = re.sub(r"\s+", " ", modelo_limpo).strip(" ;:-")
    c.carro = {
        "placa": placa,
        "renavam": renav,
        "cor": primeiro(bloco_veic, "COR"),
        "marca": inferir_marca(modelo_limpo),
        "modelo": modelo_limpo or "(não informado)",
        "ano_fab": fab,
        "ano_mod": mod,
    }
    if not c.carro["placa"]:
        c.avisos.append("NÃO achei a placa do carro")
    if fab is None:
        c.avisos.append("NÃO achei o ano do carro")
    if not c.carro["marca"]:
        c.avisos.append(f"marca não inferida de '{modelo_limpo}'")

    # Observações (valores, pagamento, 2º carro, diferença).
    mo = re.search(r"OBSERVA\S*\s*:?\s*(.*?)(?=O VE[IÍ]CULO EST|$)",
                   texto, re.I | re.S)
    c.obs = (mo.group(1).strip() if mo else "").replace("\n", " ")
    valores = todos_valores(c.obs)
    c.valor = max(valores) if valores else None
    c.forma = forma_pagamento(c.obs)
    c.data = parse_data(texto)

    md = re.search(r"(?:VOLTA|DIFEREN[ÇC]A|RECEBI).{0,40}?(R\$ ?[\d.]+)", c.obs, re.I)
    if md:
        c.diferenca = parse_dinheiro(md.group(1))

    # Carro recebido na troca (best-effort): procura placa diferente na observação.
    if c.tipo == TipoNegocio.TROCA:
        placa2 = ""
        obs_limpa = re.sub(r"RENAVA[NM]\S*", " ", c.obs, flags=re.I)  # tira 'RENAVAN'
        obs_limpa = re.sub(r"\d{11}", " ", obs_limpa)                  # tira o renavam
        for m in _PLACA_RE.finditer(obs_limpa):
            p = normalizar_placa(m.group(0))
            if p and p != c.carro["placa"] and not _parece_ano(p[3:]):
                placa2 = p
                break
        if placa2:
            fab2, mod2 = achar_ano(c.obs)
            c.carro_recebido = {
                "placa": placa2,
                "renavam": achar_renavam(c.obs),
                "cor": "",
                "marca": "",
                "modelo": "(ver observações)",
                "ano_fab": fab2,
                "ano_mod": mod2,
            }
    if c.valor is None:
        c.avisos.append("NÃO achei valor em R$")

    return c


class Command(BaseCommand):
    help = "Importa os contratos antigos (.txt) para o sistema, preservando o número."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Só mostra o que faria, sem gravar.")
        parser.add_argument("--dir", default=PASTA_PADRAO,
                            help="Pasta com os .txt dos contratos.")
        parser.add_argument("--numeros", nargs="*", type=int,
                            help="Importa só esses números de contrato.")
        parser.add_argument("--limit", type=int, help="Importa só os N primeiros.")

    def handle(self, *args, **opts):
        pasta = opts["dir"]
        arquivos = sorted(
            f for f in os.listdir(pasta)
            if f.endswith(".txt") and f != "INDICE.md" and "MODELO NOVO" not in f
        )
        contratos = [ler_contrato(os.path.join(pasta, f)) for f in arquivos]
        contratos = [c for c in contratos if c.numero]
        if opts.get("numeros"):
            contratos = [c for c in contratos if c.numero in opts["numeros"]]
        if opts.get("limit"):
            contratos = contratos[: opts["limit"]]

        dry = opts["dry_run"]
        self.stdout.write(self.style.WARNING(
            f"\n{'='*70}\n{'MODO TESTE (nada será gravado)' if dry else 'GRAVANDO NO BANCO'}"
            f"  —  {len(contratos)} contratos\n{'='*70}"))

        empresa = Empresa.objects.get(nome=EMPRESA_NOME)
        usuario = Usuario.objects.get(username=USUARIO_LOGIN)
        set_empresa_atual(empresa)
        self._sem_placa = 0
        criados = pulados = 0
        try:
            for c in contratos:
                self._mostrar(c)
                if dry:
                    continue
                try:
                    with transaction.atomic():
                        novo = self._gravar(c, empresa, usuario)
                    if novo:
                        criados += 1
                        self.stdout.write(self.style.SUCCESS("   → gravado"))
                    else:
                        pulados += 1
                        self.stdout.write("   → já existia, pulei")
                except Exception as e:
                    pulados += 1
                    self.stdout.write(self.style.ERROR(f"   → ERRO, pulei: {e}"))
        finally:
            limpar_empresa_atual()

        self.stdout.write(self.style.WARNING(f"\n{'='*70}"))
        if dry:
            com_aviso = sum(1 for c in contratos if c.avisos)
            self.stdout.write(f"Modo teste: {len(contratos)} contratos lidos, "
                              f"{com_aviso} com algum aviso pra conferir.")
            self.stdout.write("Rode sem --dry-run para gravar de verdade.")
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Pronto: {criados} gravados, {pulados} pulados."))

    def _mostrar(self, c):
        self.stdout.write(self.style.HTTP_INFO(
            f"\n#{c.numero}  {c.get_tipo_display() if hasattr(c, 'get_tipo_display') else c.tipo.upper()}  ({c.arquivo})"))
        p = c.pessoa
        self.stdout.write(f"   Pessoa : {p['nome']}  CPF {p['cpf'] or '—'}  "
                          f"tel {p['telefone'] or '—'}")
        v = c.carro
        ano = f"{v['ano_fab']}/{v['ano_mod']}" if v["ano_fab"] else "—"
        self.stdout.write(f"   Carro  : {v['marca']} {v['modelo']} {ano}  "
                          f"placa {v['placa'] or '—'}  cor {v['cor'] or '—'}")
        if c.carro_recebido:
            self.stdout.write(f"   Recebido: placa {c.carro_recebido['placa']} "
                              f"(detalhes nas observações)")
        self.stdout.write(f"   Valor  : {c.valor if c.valor is not None else '—'}  "
                          f"forma {c.forma or '—'}  data {c.data or '—'}"
                          + (f"  diferença {c.diferenca}" if c.diferenca else ""))
        for a in c.avisos:
            self.stdout.write(self.style.WARNING(f"   ⚠ {a}"))

    # ----- gravação -------------------------------------------------------

    def _pessoa(self, c, empresa, usuario):
        dados = c.pessoa
        qs = Pessoa.objetos
        achou = None
        if dados["cpf"] and len(dados["cpf"]) == 11:
            achou = qs.filter(cpf_cnpj=dados["cpf"]).first()
        if not achou and dados["nome"]:
            achou = qs.filter(nome__iexact=dados["nome"]).first()
        if achou:
            return achou
        return Pessoa.objetos.create(
            tipo=TipoPessoa.FISICA,
            nome=dados["nome"] or "(sem nome)",
            cpf_cnpj=dados["cpf"] if len(dados["cpf"]) in (11, 14) else "",
            telefone=dados["telefone"],
            rg=dados["rg"][:20],
            endereco=dados["endereco"][:200],
            observacoes=MARCA_IMPORT,
            criado_por=usuario,
        )

    def _veiculo(self, dados, empresa, usuario, situacao, status, **extra):
        placa = (dados.get("placa") or "").strip()
        renav = dados.get("renavam", "") if len(dados.get("renavam", "")) == 11 else ""
        # Reaproveita por placa OU renavam (evita duplicar e reconcilia OCR torto).
        achou = None
        if placa:
            achou = Veiculo.objetos.filter(placa=placa).first()
        if not achou and renav:
            achou = Veiculo.objetos.filter(renavam=renav).first()
        if achou:
            return achou
        obs = MARCA_IMPORT
        if not placa:
            self._sem_placa += 1
            placa = f"SPL{self._sem_placa:04d}"  # placeholder único (placa não veio no contrato)
            obs += " | PLACA AUSENTE NO CONTRATO (placeholder, conferir)"
        return Veiculo.objetos.create(
            placa=placa,
            marca=dados.get("marca", "")[:60] or "(a conferir)",
            modelo=dados.get("modelo", "")[:120] or "(a conferir)",
            ano_fabricacao=dados.get("ano_fab") or 0,
            ano_modelo=dados.get("ano_mod") or dados.get("ano_fab") or 0,
            cor=dados.get("cor", "")[:40],
            renavam=renav,
            cambio=Cambio.MANUAL,
            situacao=situacao,
            status=status,
            observacoes=obs,
            criado_por=usuario,
            **extra,
        )

    def _gravar(self, c, empresa, usuario):
        # idempotência: mesmo número + mesma pessoa + marca de import => já existe.
        existe = (Negocio.objetos
                  .filter(numero_contrato=c.numero,
                          observacoes__contains=MARCA_IMPORT,
                          partes__pessoa__nome__iexact=(c.pessoa["nome"] or "x"))
                  .exists())
        if existe:
            return False

        pessoa = self._pessoa(c, empresa, usuario)
        obs_completa = f"{MARCA_IMPORT}\nContrato nº {c.numero} — {c.arquivo}\n\n{c.obs}"

        negocio = Negocio.objetos.create(
            tipo=c.tipo,
            modalidade=Modalidade.PROPRIA,
            numero_contrato=c.numero,
            data=c.data or datetime.date.today(),
            forma_pagamento=c.forma,
            valor_total=c.valor,
            diferenca=c.diferenca,
            status=StatusNegocio.CONCLUIDO,
            observacoes=obs_completa,
            criado_por=usuario,
        )
        valor = c.valor or Decimal("0")

        if c.tipo == TipoNegocio.VENDA:
            carro = self._veiculo(c.carro, empresa, usuario,
                                  Situacao.PROPRIO, StatusVeiculo.VENDIDO,
                                  valor_anunciado=valor)
            ItemNegocio.objetos.create(negocio=negocio, veiculo=carro, valor=valor,
                                       para_pessoa=pessoa, km_entrega=None,
                                       criado_por=usuario)
            ParteNegocio.objetos.create(negocio=negocio, pessoa=pessoa,
                                        papel=PapelParte.COMPRADOR, criado_por=usuario)

        elif c.tipo == TipoNegocio.COMPRA:
            carro = self._veiculo(c.carro, empresa, usuario,
                                  Situacao.PROPRIO, StatusVeiculo.EM_ESTOQUE,
                                  valor_compra=valor)
            ItemNegocio.objetos.create(negocio=negocio, veiculo=carro, valor=valor,
                                       de_pessoa=pessoa, criado_por=usuario)
            ParteNegocio.objetos.create(negocio=negocio, pessoa=pessoa,
                                        papel=PapelParte.VENDEDOR, criado_por=usuario)

        else:  # TROCA — carro da loja sai, carro do cliente entra (se identificado)
            saindo = self._veiculo(c.carro, empresa, usuario,
                                   Situacao.PROPRIO, StatusVeiculo.VENDIDO,
                                   valor_anunciado=valor)
            ItemNegocio.objetos.create(negocio=negocio, veiculo=saindo, valor=valor,
                                       para_pessoa=pessoa, criado_por=usuario)
            if c.carro_recebido:
                entrando = self._veiculo(c.carro_recebido, empresa, usuario,
                                         Situacao.PROPRIO, StatusVeiculo.EM_ESTOQUE,
                                         valor_compra=Decimal("0"))
                ItemNegocio.objetos.create(negocio=negocio, veiculo=entrando,
                                           valor=Decimal("0"), de_pessoa=pessoa,
                                           criado_por=usuario)
            ParteNegocio.objetos.create(negocio=negocio, pessoa=pessoa,
                                        papel=PapelParte.PERMUTANTE, criado_por=usuario)

        return True
