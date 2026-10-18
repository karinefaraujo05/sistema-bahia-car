"""Remapeia os valores antigos de forma_pagamento para os novos (item 4.3).

À vista → Dinheiro, Parcelado na loja → Financiamento, Misto → Troca + dinheiro.
'financiado' continua igual. Pix e Cartão são novos (não havia equivalente antigo).
"""

from django.db import migrations

MAPA = {
    "a_vista": "dinheiro",
    "parcelado_loja": "financiado",
    "misto": "troca_dinheiro",
}


def remapear(apps, schema_editor):
    for nome_modelo in ("Negocio", "HistoricalNegocio"):
        try:
            Modelo = apps.get_model("negocios", nome_modelo)
        except LookupError:
            continue
        gerente = Modelo._base_manager  # sem filtro de empresa/arquivado
        for antigo, novo in MAPA.items():
            gerente.filter(forma_pagamento=antigo).update(forma_pagamento=novo)


class Migration(migrations.Migration):
    dependencies = [
        ("negocios", "0003_alter_historicalnegocio_forma_pagamento_and_more"),
    ]

    operations = [
        migrations.RunPython(remapear, migrations.RunPython.noop),
    ]
