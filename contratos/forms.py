from django import forms

from .models import ConfiguracaoLoja, TipoDocumento


class ConfiguracaoLojaForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoLoja
        fields = [
            "razao_social",
            "cnpj",
            "endereco",
            "cidade",
            "uf",
            "cep",
            "representante_nome",
            "representante_cpf",
            "multa_percentual",
            "regra_ipva",
            "prazo_assinatura_dias",
            "prazo_repasse_dias",
            "numero_vias",
        ]

    _NUMERICOS = {
        "cnpj",
        "cep",
        "representante_cpf",
        "multa_percentual",
        "prazo_assinatura_dias",
        "prazo_repasse_dias",
        "numero_vias",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nome, campo in self.fields.items():
            campo.widget.attrs.setdefault("class", "campo")
            if nome in self._NUMERICOS:
                campo.widget.attrs.setdefault("inputmode", "numeric")


class DocumentoUploadForm(forms.Form):
    """Dados do upload. Os arquivos em si vêm em request.FILES (campo 'arquivos')."""

    tipo = forms.ChoiceField(label="Tipo de documento", choices=TipoDocumento.choices)
    descricao = forms.CharField(label="Descrição (opcional)", required=False)
    juntar_pdf = forms.BooleanField(
        label="Juntar as imagens num único PDF", required=False, initial=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo"].widget.attrs["class"] = "campo"
        self.fields["descricao"].widget.attrs["class"] = "campo"
