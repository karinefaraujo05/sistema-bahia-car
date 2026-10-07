"""Mensagem motivacional do dia (muda a cada dia, igual pra todos os acessos do dia)."""

FRASES = [
    "Cada carro vendido é uma família feliz saindo com você. Bora pra cima!",
    "Negócio bom é o que fecha com confiança dos dois lados. Capriche no atendimento.",
    "Um sorriso na chegada vende mais que qualquer desconto.",
    "Hoje é dia de transformar quem entra olhando em quem sai dirigindo.",
    "Preço justo, conversa honesta: é assim que se constrói freguesia.",
    "Carro parado é dinheiro parado. Dá aquele empurrãozinho nos que estão há mais tempo.",
    "Quem cuida dos detalhes fecha mais negócios. Confira as fotos e os preços.",
    "O cliente de hoje é a indicação de amanhã. Trate cada um como único.",
    "Organização é lucro: contrato certo, documento no lugar, cabeça tranquila.",
    "Grandes lojas começaram com um carro bem vendido. Siga firme.",
    "Confiança não se anuncia, se demonstra. Boa semana de vendas!",
    "Foco no cliente, olho no estoque e fé no trabalho. O resto vem.",
    "Todo dia é uma chance nova de bater a meta. Vamos juntos!",
    "Atenção ao que precisa de ação: a agenda está te esperando.",
    "Vender é ajudar alguém a realizar um sonho sobre rodas.",
]


def frase_do_dia(data):
    """Retorna a frase do dia (determinística: a mesma o dia todo, muda a cada dia)."""
    return FRASES[data.toordinal() % len(FRASES)]
