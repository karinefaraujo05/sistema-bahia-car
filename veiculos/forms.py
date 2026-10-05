from django import forms

from .models import Veiculo
from .validators import normalizar_placa


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

    def clean_placa(self):
        placa = normalizar_placa(self.cleaned_data["placa"])
        existe = Veiculo.objetos.filter(placa=placa)
        if self.instance.pk:
            existe = existe.exclude(pk=self.instance.pk)
        if existe.exists():
            raise forms.ValidationError("Essa placa já está cadastrada em outro carro.")
        return placa
