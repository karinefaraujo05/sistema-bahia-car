from django import forms

from core.dados_br import ESTADO_CIVIL_CHOICES, UF_CHOICES

from .models import Pessoa, TipoPessoa
from .validators import so_digitos

# Campos que pedem teclado numérico no celular.
_NUMERICOS = {"telefone", "cpf_cnpj", "cep", "representante_cpf"}


def _estilizar(form):
    for nome, campo in form.fields.items():
        widget = campo.widget
        if isinstance(widget, forms.CheckboxInput):
            continue
        if isinstance(widget, forms.Textarea):
            widget.attrs.setdefault("rows", 3)
        widget.attrs.setdefault("class", "campo")
        if nome in _NUMERICOS:
            widget.attrs.setdefault("inputmode", "numeric")


def _checar_coerencia_documento(form, tipo, documento):
    """Adiciona erro se o documento não bate com o tipo (física=CPF, jurídica=CNPJ)."""
    if not documento:
        return
    if tipo == TipoPessoa.FISICA and len(documento) == 14:
        form.add_error("cpf_cnpj", "Pessoa física usa CPF (11 dígitos), não CNPJ.")
    elif tipo == TipoPessoa.JURIDICA and len(documento) == 11:
        form.add_error("cpf_cnpj", "Pessoa jurídica usa CNPJ (14 dígitos), não CPF.")


class PessoaRapidaForm(forms.ModelForm):
    class Meta:
        model = Pessoa
        # Cadastro rápido agora pede o CPF/CNPJ: evita pessoa duplicada e já adianta
        # o que o contrato precisa. O resto (endereço, RG...) fica pra depois.
        fields = ["tipo", "cpf_cnpj", "nome", "telefone"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cpf_cnpj"].required = True
        _estilizar(self)

    def clean_cpf_cnpj(self):
        return so_digitos(self.cleaned_data.get("cpf_cnpj"))

    def clean(self):
        dados = super().clean()
        _checar_coerencia_documento(self, dados.get("tipo"), dados.get("cpf_cnpj"))
        return dados


class PessoaForm(forms.ModelForm):
    # Campos que viram seleção (menos digitação, menos erro).
    uf = forms.ChoiceField(label="UF", required=False, choices=[("", "escolher…"), *UF_CHOICES])
    estado_civil = forms.ChoiceField(
        label="estado civil", required=False, choices=[("", "escolher…"), *ESTADO_CIVIL_CHOICES]
    )

    class Meta:
        model = Pessoa
        fields = [
            "tipo",
            "nome",
            "cpf_cnpj",
            "telefone",
            "email",
            "endereco",
            "cidade",
            "uf",
            "cep",
            "rg",
            "rg_orgao_emissor",
            "nacionalidade",
            "estado_civil",
            "profissao",
            "representante_nome",
            "representante_cpf",
            "observacoes",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _estilizar(self)
        # Obrigatórios: nome (do modelo) e CPF/CNPJ. O resto a pessoa completa depois
        # (a cobrança de completude acontece na hora de gerar o contrato).
        self.fields["cpf_cnpj"].required = True
        self.fields["cep"].required = False
        self.fields["cep"].help_text = "Digite o CEP e o endereço é preenchido sozinho."
        self.fields["observacoes"].label = "Observações sobre a pessoa"
        # Nacionalidade: lista de sugestões (datalist) com padrão "Brasileira".
        self.fields["nacionalidade"].widget.attrs["list"] = "nacionalidades"
        if not self.instance.pk and not self.is_bound:
            self.fields["nacionalidade"].initial = "Brasileira"
        # Não perder valores antigos fora da lista ao editar (ex.: estado civil digitado antes).
        for campo in ("uf", "estado_civil"):
            atual = getattr(self.instance, campo, "") or ""
            if atual and atual not in [v for v, _ in self.fields[campo].choices]:
                self.fields[campo].choices = [(atual, atual), *self.fields[campo].choices]

    def clean_cpf_cnpj(self):
        documento = so_digitos(self.cleaned_data.get("cpf_cnpj"))
        if documento:
            existe = Pessoa.objetos.filter(cpf_cnpj=documento)
            if self.instance.pk:
                existe = existe.exclude(pk=self.instance.pk)
            if existe.exists():
                raise forms.ValidationError("Esse CPF/CNPJ já está cadastrado em outra pessoa.")
        return documento

    def clean(self):
        dados = super().clean()
        _checar_coerencia_documento(self, dados.get("tipo"), dados.get("cpf_cnpj"))
        return dados
