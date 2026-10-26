from django import forms

from .models import GastoVeiculo, Veiculo
from .validators import normalizar_placa


class GastoVeiculoForm(forms.ModelForm):
    class Meta:
        model = GastoVeiculo
        fields = ["descricao", "valor", "data"]
        widgets = {"data": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["data"].required = False
        for campo in self.fields.values():
            campo.widget.attrs.setdefault("class", "campo")
        self.fields["valor"].widget.attrs["inputmode"] = "numeric"
        self.fields["descricao"].widget.attrs["placeholder"] = "Ex.: funilaria, documentação, pneus"


class VeiculoForm(forms.ModelForm):
    class Meta:
        model = Veiculo
        fields = [
            "placa",
            "marca",
            "modelo",
            "ano_fabricacao",
            "ano_modelo",
            "cor",
            "km",
            "combustivel",
            "cambio",
            "chassi",
            "renavam",
            "situacao",
            "proprietario_registral",
            "valor_compra",
            "valor_anunciado",
            "valor_fipe",
            "status",
            "alienado",
            "credor_alienacao",
            "saldo_devedor",
            "parcelas_restantes",
            "valor_parcela",
            "dia_vencimento",
            "parcelas_vencidas",
            "tem_chave_reserva",
            "avarias_declaradas",
            "sinistro_declarado",
            "sinistro_descricao",
            "observacoes",
        ]

    # Campos que pedem teclado numérico no celular.
    _NUMERICOS = {
        "km",
        "valor_compra",
        "valor_anunciado",
        "saldo_devedor",
        "parcelas_restantes",
        "valor_parcela",
        "dia_vencimento",
        "parcelas_vencidas",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nome, campo in self.fields.items():
            widget = campo.widget
            if isinstance(widget, forms.CheckboxInput):
                continue
            if isinstance(widget, forms.Textarea):
                widget.attrs.setdefault("rows", 3)
            widget.attrs.setdefault("class", "campo")
            if nome in self._NUMERICOS:
                widget.attrs.setdefault("inputmode", "numeric")
        # Cor: dropdown com todas as cores (datalist no template), mas ainda dá pra
        # digitar uma cor fora da lista (ex.: "Branco Perolizado").
        self.fields["cor"].widget.attrs["list"] = "cores-carro"
        self.fields["cor"].widget.attrs.setdefault("placeholder", "Escolha ou digite")
        # Credor do financiamento: lista de bancos/financeiras comuns (dá pra digitar outro).
        self.fields["credor_alienacao"].widget.attrs["list"] = "credores"
        # valor_fipe é preenchido pela consulta FIPE (JS) e fica escondido no form.
        self.fields["valor_fipe"].widget = forms.HiddenInput()

    def clean_placa(self):
        placa = normalizar_placa(self.cleaned_data["placa"])
        existe = Veiculo.objetos.filter(placa=placa)
        if self.instance.pk:
            existe = existe.exclude(pk=self.instance.pk)
        if existe.exists():
            raise forms.ValidationError("Essa placa já está cadastrada em outro carro.")
        return placa
