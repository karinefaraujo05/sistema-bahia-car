"""
Contexto normalizado para o PDF bonito (modelo "MARA"), montado a partir dos
dados do negócio e adaptado por tipo: venda, compra, troca e venda de terceiro
(intermediação). A consignação (modelo D) usa o render antigo por enquanto.
"""

from negocios.models import PapelParte
from negocios.services import diferenca_troca

from .models import ConfiguracaoLoja, ModeloContrato


def _veiculo_de(v, km=None, valor=None):
    return {
        "marca_modelo": f"{v.marca} {v.modelo}".strip(),
        "ano": f"{v.ano_fabricacao}/{v.ano_modelo}",
        "cor": v.cor,
        "combustivel": v.get_combustivel_display() if v.combustivel else "",
        "placa": v.placa_formatada,
        "renavam": v.renavam or "",
        "chassi": v.chassi or "",
        "km": km,
        "chave": "Sim" if v.tem_chave_reserva else "Não",
        "avarias": v.avarias_declaradas or "Nenhuma aparente",
        "valor": valor,
    }


def _veiculo(item):
    return _veiculo_de(item.veiculo, item.km_entrega, item.valor)


def _contexto_consignacao(contrato, loja):
    cons = contrato.consignacao
    return {
        "loja": loja,
        "contrato": contrato,
        "titulo": contrato.titulo,
        "numero": cons.numero_contrato,
        "data": cons.data_entrada,
        "cidade_uf": f"{loja.cidade}/{loja.uf}",
        "multa_pct": loja.multa_percentual or 10,
        "eh_troca": False,
        "eh_consignacao": True,
        "interveniente": None,
        "consignante": _pessoa_parte("CONSIGNANTE", cons.proprietario),
        "consignataria": _loja_parte("CONSIGNATÁRIA", loja),
        "veiculo": _veiculo_de(cons.veiculo),
        "valor_minimo": cons.valor_liquido_minimo,
        "comissao_tipo": cons.comissao_tipo,
        "comissao_valor": cons.comissao_valor,
        "prazo_dias": cons.prazo_dias,
        "aviso_dias": cons.aviso_dias,
        "prazo_repasse_dias": cons.prazo_repasse_dias,
        "documentos": cons.documentos_entregues or "—",
    }


def _loja_parte(rotulo, loja):
    return {
        "rotulo": rotulo,
        "eh_loja": True,
        "nome": (loja.razao_social or "").upper(),
        "fantasia": loja.nome_fantasia or "Bahia Car",
    }


def _pessoa_parte(rotulo, pessoa):
    return {"rotulo": rotulo, "eh_loja": False, "pessoa": pessoa}


def contexto_mara(contrato):
    loja = ConfiguracaoLoja.carregar()
    if contrato.consignacao_id:
        return _contexto_consignacao(contrato, loja)
    negocio = contrato.negocio
    partes = list(negocio.partes.select_related("pessoa"))

    def pessoa(papel):
        return next((p.pessoa for p in partes if p.papel == papel), None)

    itens = list(negocio.itens.select_related("veiculo"))
    item = itens[0] if itens else None
    modelo = contrato.modelo

    ctx = {
        "loja": loja,
        "negocio": negocio,
        "contrato": contrato,
        "numero": negocio.numero_contrato,
        "data": negocio.data,
        "titulo": contrato.titulo,
        "multa_pct": loja.multa_percentual or 10,
        "cidade_uf": f"{loja.cidade}/{loja.uf}",
        "eh_troca": False,
        "eh_consignacao": False,
        "interveniente": None,
    }

    if modelo == ModeloContrato.C:  # troca / permuta: dois carros
        saida = next((i for i in itens if i.sai_da_loja), None)
        entradas = [i for i in itens if i.entra_na_loja]
        ctx.update(
            {
                "eh_troca": True,
                "parte_a": _loja_parte("PERMUTANTE 1 — LOJA", loja),
                "parte_b": _pessoa_parte("PERMUTANTE 2 — CLIENTE", pessoa(PapelParte.PERMUTANTE)),
                "veiculo_loja": _veiculo(saida) if saida else None,
                "veiculo_cliente": _veiculo(entradas[0]) if entradas else None,
                "diferenca": diferenca_troca(negocio),
                "diferenca_abs": abs(diferenca_troca(negocio) or 0),
            }
        )
        return ctx

    if modelo == ModeloContrato.A:  # compra: a loja compra da pessoa
        vendedor = _pessoa_parte("VENDEDOR(A)", pessoa(PapelParte.VENDEDOR))
        comprador = _loja_parte("COMPRADOR(A)", loja)
    elif modelo == ModeloContrato.E:  # venda de terceiro (intermediação)
        vendedor = _pessoa_parte("VENDEDOR(A)", pessoa(PapelParte.VENDEDOR))
        comprador = _pessoa_parte("COMPRADOR(A)", pessoa(PapelParte.COMPRADOR))
        ctx["interveniente"] = loja
    else:  # B — venda: a loja vende
        vendedor = _loja_parte("VENDEDOR(A)", loja)
        comprador = _pessoa_parte("COMPRADOR(A)", pessoa(PapelParte.COMPRADOR))

    ctx.update(
        {
            "vendedor": vendedor,
            "comprador": comprador,
            "veiculo": _veiculo(item) if item else None,
            "valor": item.valor if item else None,
            "forma_pagamento": negocio.get_forma_pagamento_display()
            if negocio.forma_pagamento
            else "",
            "detalhes_pagamento": negocio.detalhes_pagamento or "",
        }
    )
    return ctx
