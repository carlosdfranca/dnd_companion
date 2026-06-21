from django import forms
from django.forms import inlineformset_factory

from .models import (
    Personagem, Pericia, Salvaguarda, RecursoDeCombate,
    ItemInventario, Local, NPC, Missao, ResumoSessao, InformacaoImportante,
    NotaCombate,
)


class BootstrapFormMixin:
    """Adiciona classes Bootstrap automaticamente a todos os widgets do form."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            w = field.widget
            if isinstance(w, (forms.TextInput, forms.NumberInput, forms.EmailInput,
                               forms.URLInput, forms.PasswordInput)):
                w.attrs.setdefault("class", "form-control")
            elif isinstance(w, forms.DateInput):
                w.attrs.setdefault("class", "form-control")
                w.attrs.setdefault("type", "date")
            elif isinstance(w, forms.Select):
                w.attrs.setdefault("class", "form-select")
            elif isinstance(w, forms.Textarea):
                w.attrs.setdefault("class", "form-control")
                w.attrs.setdefault("rows", "4")
            elif isinstance(w, forms.CheckboxInput):
                w.attrs.setdefault("class", "form-check-input")


class PersonagemForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Personagem
        exclude = ["criado_em", "atualizado_em"]
        widgets = {
            "background": forms.Textarea(attrs={"rows": 6}),
        }


class PericiaForm(forms.ModelForm):
    class Meta:
        model = Pericia
        fields = ["proficiente"]
        widgets = {
            "proficiente": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class SalvaguardaForm(forms.ModelForm):
    class Meta:
        model = Salvaguarda
        fields = ["proficiente"]
        widgets = {
            "proficiente": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


PericiaFormSet = inlineformset_factory(
    Personagem, Pericia,
    form=PericiaForm,
    extra=0,
    can_delete=False,
)

SalvaguardaFormSet = inlineformset_factory(
    Personagem, Salvaguarda,
    form=SalvaguardaForm,
    extra=0,
    can_delete=False,
)


class RecursoDeCombateForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = RecursoDeCombate
        exclude = ["personagem"]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 3}),
            "checklist_turno": forms.Textarea(attrs={"rows": 3}),
        }


class ItemInventarioForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ItemInventario
        exclude = ["personagem"]
        widgets = {
            "atributos_efeito": forms.Textarea(attrs={"rows": 3}),
            "lore": forms.Textarea(attrs={"rows": 5}),
        }


class LocalForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Local
        fields = "__all__"
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 4}),
        }


class NPCForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = NPC
        fields = "__all__"
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 4}),
        }


class MissaoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Missao
        fields = "__all__"
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 4}),
            "resultado": forms.Textarea(attrs={"rows": 3}),
        }


class ResumoSessaoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ResumoSessao
        fields = "__all__"
        widgets = {
            "resumo": forms.Textarea(attrs={"rows": 12}),
        }


class InformacaoImportanteForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = InformacaoImportante
        fields = "__all__"


class NotaCombateForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = NotaCombate
        fields = ["titulo", "conteudo", "ordem"]
        widgets = {
            "conteudo": forms.Textarea(attrs={
                "rows": 8,
                "placeholder": "Descreva a mecânica, dano, condições...\nFormatação livre — quebras de linha são preservadas.",
                "style": "font-family: monospace; font-size: .88rem;",
            }),
        }
