from django import forms

from pessoas.models import Pessoa

from .models import ComissaoTipo, FormaPagamento, QuitacaoOpcao


def _campo_classe(form):
    for campo in form.fields.values():
        widget = campo.widget
        if isinstance(widget, forms.CheckboxInput):
            continue
        if isinstance(widget, forms.Textarea):
            widget.attrs.setdefault("rows", 3)
        widget.attrs.setdefault("class", "campo")


class EscolherPessoaForm(forms.Form):
    """Escolhe uma pessoa já cadastrada para o negócio."""

    pessoa = forms.ModelChoiceField(
        queryset=Pessoa.objetos.all(),
        required=True,
        label="Pessoa já cadastrada",
        empty_label="escolher…",
        error_messages={
            "required": "Escolha a pessoa. Se ela ainda não existe, cadastre primeiro no botão abaixo.",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _campo_classe(self)

    def resolver(self, usuario=None):
        return self.cleaned_data["pessoa"]


class EscolherCarroForm(forms.Form):
    """Escolhe um carro de uma lista (estoque)."""

    veiculo = forms.ModelChoiceField(queryset=None, label="Carro", empty_label="escolher…")

    def __init__(self, *args, queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["veiculo"].queryset = queryset
        _campo_classe(self)


class PagamentoEntregaForm(forms.Form):
    valor = forms.DecimalField(label="Valor do carro (R$)", max_digits=10, decimal_places=2)
    km_entrega = forms.IntegerField(label="Quilometragem na entrega", required=False)
    forma_pagamento = forms.ChoiceField(
        label="Forma de pagamento",
        choices=[("", "escolher…"), *FormaPagamento.choices],
        required=False,
    )
    detalhes_pagamento = forms.CharField(
        label="Detalhes do pagamento", widget=forms.Textarea, required=False
    )
    data = forms.DateField(label="Data do negócio", widget=forms.DateInput(attrs={"type": "date"}))
    data_hora_entrega = forms.DateTimeField(
        label="Data e hora da entrega",
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
    )
    local_entrega = forms.CharField(label="Local da entrega", required=False)

    # Só aparece quando o carro é alienado (preenchido pela view).
    quitacao_opcao = forms.ChoiceField(
        label="Como fica a quitação do financiamento",
        choices=[("", "escolher…"), *QuitacaoOpcao.choices],
        required=False,
    )

    def __init__(self, *args, exige_quitacao=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["valor"].widget.attrs["inputmode"] = "numeric"
        self.fields["km_entrega"].widget.attrs["inputmode"] = "numeric"
        if not exige_quitacao:
            del self.fields["quitacao_opcao"]
        _campo_classe(self)

    def clean_quitacao_opcao(self):
        valor = self.cleaned_data.get("quitacao_opcao")
        if "quitacao_opcao" in self.fields and not valor:
            raise forms.ValidationError(
                "Esse carro tem financiamento: escolha como fica a quitação."
            )
        return valor


class TrocaValoresForm(forms.Form):
    valor_loja = forms.DecimalField(
        label="Valor do carro da loja (R$)", max_digits=10, decimal_places=2
    )
    valor_cliente = forms.DecimalField(
        label="Valor do carro do cliente (R$)", max_digits=10, decimal_places=2
    )
    km_loja = forms.IntegerField(label="Km do carro da loja na entrega", required=False)
    km_cliente = forms.IntegerField(label="Km do carro do cliente na entrega", required=False)
    forma_pagamento = forms.ChoiceField(
        label="Forma de pagamento da diferença",
        choices=[("", "escolher…"), *FormaPagamento.choices],
        required=False,
    )
    detalhes_pagamento = forms.CharField(
        label="Detalhes do pagamento", widget=forms.Textarea, required=False
    )
    data = forms.DateField(label="Data do negócio", widget=forms.DateInput(attrs={"type": "date"}))
    data_hora_entrega = forms.DateTimeField(
        label="Data e hora da entrega",
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
    )
    local_entrega = forms.CharField(label="Local da entrega", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nome in ("valor_loja", "valor_cliente", "km_loja", "km_cliente"):
            self.fields[nome].widget.attrs["inputmode"] = "numeric"
        _campo_classe(self)


class ConsignacaoTermosForm(forms.Form):
    valor_liquido_minimo = forms.DecimalField(
        label="Valor mínimo que o dono recebe (R$)", max_digits=10, decimal_places=2
    )
    comissao_tipo = forms.ChoiceField(label="Tipo de comissão", choices=ComissaoTipo.choices)
    comissao_valor = forms.DecimalField(
        label="Valor da comissão (R$ ou %)", max_digits=10, decimal_places=2, required=False
    )
    prazo_dias = forms.IntegerField(label="Prazo (dias)", initial=90)
    aviso_dias = forms.IntegerField(label="Aviso de encerramento (dias)", initial=15)
    prazo_repasse_dias = forms.IntegerField(label="Prazo de repasse (dias)", initial=5)
    documentos_entregues = forms.CharField(
        label="Documentos entregues pelo dono", widget=forms.Textarea, required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nome in ("valor_liquido_minimo", "comissao_valor"):
            self.fields[nome].widget.attrs["inputmode"] = "numeric"
        _campo_classe(self)

    def clean(self):
        dados = super().clean()
        if dados.get("comissao_tipo") != ComissaoTipo.SOBREPRECO and not dados.get(
            "comissao_valor"
        ):
            self.add_error("comissao_valor", "Informe o valor da comissão.")
        return dados
