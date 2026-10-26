"""
Listas fixas do Brasil, reutilizadas em formulários (selects) e em outros lugares.

Fonte única: antes a lista de estados vivia duplicada (negocios/views.py). Aqui ela
serve tanto para os selects de UF quanto para o nome do estado por extenso.
"""

# (sigla, nome) dos 27 estados + DF.
UFS = [
    ("AC", "Acre"),
    ("AL", "Alagoas"),
    ("AP", "Amapá"),
    ("AM", "Amazonas"),
    ("BA", "Bahia"),
    ("CE", "Ceará"),
    ("DF", "Distrito Federal"),
    ("ES", "Espírito Santo"),
    ("GO", "Goiás"),
    ("MA", "Maranhão"),
    ("MT", "Mato Grosso"),
    ("MS", "Mato Grosso do Sul"),
    ("MG", "Minas Gerais"),
    ("PA", "Pará"),
    ("PB", "Paraíba"),
    ("PR", "Paraná"),
    ("PE", "Pernambuco"),
    ("PI", "Piauí"),
    ("RJ", "Rio de Janeiro"),
    ("RN", "Rio Grande do Norte"),
    ("RS", "Rio Grande do Sul"),
    ("RO", "Rondônia"),
    ("RR", "Roraima"),
    ("SC", "Santa Catarina"),
    ("SP", "São Paulo"),
    ("SE", "Sergipe"),
    ("TO", "Tocantins"),
]

# Para selects: value = sigla, rótulo = "BA — Bahia".
UF_CHOICES = [(sigla, f"{sigla} — {nome}") for sigla, nome in UFS]

# Nome por extenso a partir da sigla (ex.: "BA" -> "Bahia").
UF_POR_EXTENSO = dict(UFS)

# Estado civil (o rótulo também é o valor guardado, pra sair bonito no contrato).
ESTADOS_CIVIS = [
    "Solteiro(a)",
    "Casado(a)",
    "Divorciado(a)",
    "Viúvo(a)",
    "União estável",
    "Separado(a)",
]
ESTADO_CIVIL_CHOICES = [(e, e) for e in ESTADOS_CIVIS]
