from django.db.models import F
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.views.decorators.http import require_POST
from django.urls import reverse_lazy

from .models import (
    Personagem, RecursoDeCombate, ItemInventario,
    Local, NPC, Missao, ResumoSessao, InformacaoImportante, NotaCombate,
)
from .forms import (
    PersonagemForm, PericiaFormSet, SalvaguardaFormSet,
    RecursoDeCombateForm, ItemInventarioForm,
    LocalForm, NPCForm, MissaoForm, ResumoSessaoForm, InformacaoImportanteForm,
    NotaCombateForm,
)
from .utils import get_current_character


# ── Dashboard ─────────────────────────────────────────────────────────────────

def dashboard(request):
    from . import constants
    personagem = get_current_character(request)
    pv_pct = 0
    atributos_data = []
    pericias = []
    salvaguardas = []
    if personagem:
        if personagem.pv_maximo:
            pv_pct = max(0, min(100, round(personagem.pv_atual * 100 / personagem.pv_maximo)))
        atributos_data = [
            {
                "attr": attr,
                "label": label,
                "abrev": abrev,
                "score": getattr(personagem, attr),
                "mod": personagem.modificador(attr),
            }
            for attr, label, abrev in constants.ATRIBUTOS
        ]
        pericias = sorted(personagem.pericias.all(), key=lambda p: p.ordem)
        salvaguardas = sorted(personagem.salvaguardas.all(), key=lambda s: s.ordem)
    missoes_ativas = Missao.objects.filter(status="ativa")
    infos = InformacaoImportante.objects.all()
    return render(request, "campanha/dashboard.html", {
        "personagem": personagem,
        "pv_pct": pv_pct,
        "atributos_data": atributos_data,
        "pericias": pericias,
        "salvaguardas": salvaguardas,
        "missoes_ativas": missoes_ativas,
        "infos": infos,
    })


# ── Ficha ─────────────────────────────────────────────────────────────────────

def ficha(request):
    from . import constants
    personagem = get_current_character(request)
    if not personagem:
        return render(request, "campanha/sem_personagem.html")
    pv_pct = max(0, min(100, round(personagem.pv_atual * 100 / max(1, personagem.pv_maximo))))
    pericias = sorted(personagem.pericias.all(), key=lambda p: p.ordem)
    salvaguardas = sorted(personagem.salvaguardas.all(), key=lambda s: s.ordem)
    atributos_data = [
        {
            "attr": attr,
            "label": label,
            "abrev": abrev,
            "score": getattr(personagem, attr),
            "mod": personagem.modificador(attr),
        }
        for attr, label, abrev in constants.ATRIBUTOS
    ]
    return render(request, "campanha/ficha.html", {
        "personagem": personagem,
        "pv_pct": pv_pct,
        "pericias": pericias,
        "salvaguardas": salvaguardas,
        "atributos_data": atributos_data,
    })


class FichaEditView(View):
    template_name = "campanha/ficha_editar.html"

    def _get_personagem(self):
        return get_current_character(self.request)

    def get(self, request):
        p = self._get_personagem()
        pericias_fs = PericiaFormSet(instance=p, prefix="pericias")
        salvaguardas_fs = SalvaguardaFormSet(instance=p, prefix="salvaguardas")
        # Attach instance to each form so template can read rotulo/atributo
        for frm in pericias_fs.forms:
            frm.instance_obj = frm.instance
        for frm in salvaguardas_fs.forms:
            frm.instance_obj = frm.instance
        return render(request, self.template_name, {
            "form": PersonagemForm(instance=p),
            "pericia_fs": pericias_fs,
            "salvaguarda_fs": salvaguardas_fs,
            "personagem": p,
        })

    def post(self, request):
        p = self._get_personagem()
        form = PersonagemForm(request.POST, instance=p)
        pericia_fs = PericiaFormSet(request.POST, instance=p, prefix="pericias")
        salvaguarda_fs = SalvaguardaFormSet(request.POST, instance=p, prefix="salvaguardas")
        if form.is_valid() and pericia_fs.is_valid() and salvaguarda_fs.is_valid():
            form.save()
            pericia_fs.save()
            salvaguarda_fs.save()
            return redirect("ficha")
        return render(request, self.template_name, {
            "form": form,
            "pericia_fs": pericia_fs,
            "salvaguarda_fs": salvaguarda_fs,
            "personagem": p,
        })


# ── Central de Combate ────────────────────────────────────────────────────────

def central_combate(request):
    personagem = get_current_character(request)
    pv_pct = 0
    recursos_com_pips = []
    itens_equipados = []
    dado_range = range(0)
    if personagem:
        if personagem.pv_maximo:
            pv_pct = max(0, min(100, round(personagem.pv_atual * 100 / personagem.pv_maximo)))
        for r in personagem.recursos.all():
            pips = [i < r.usos_restantes for i in range(r.usos_totais)]
            recursos_com_pips.append({"recurso": r, "pips": pips})
        itens_equipados = personagem.itens.filter(tipo="equipado")
        dado_range = range(personagem.nivel)
        notas_combate = personagem.notas_combate.all()
    return render(request, "campanha/central_combate.html", {
        "personagem": personagem,
        "pv_pct": pv_pct,
        "recursos_com_pips": recursos_com_pips,
        "itens_equipados": itens_equipados,
        "dado_range": dado_range,
        "notas_combate": notas_combate,
    })


@require_POST
def atualizar_pv(request):
    p = get_current_character(request)
    if p:
        acao = request.POST.get("acao", "set")

        if acao == "dano":
            # Temp HP absorve primeiro; dano negativo ignorado
            dano = max(0, int(request.POST.get("valor", 0)))
            if p.pv_temporario > 0:
                absorvido = min(dano, p.pv_temporario)
                p.pv_temporario -= absorvido
                dano -= absorvido
            p.pv_atual = max(-p.pv_maximo, p.pv_atual - dano)
            p.save(update_fields=["pv_atual", "pv_temporario"])

        elif acao == "cura":
            cura = max(0, int(request.POST.get("valor", 0)))
            p.pv_atual = min(p.pv_maximo, p.pv_atual + cura)
            p.save(update_fields=["pv_atual"])

        elif acao == "delta":
            delta = int(request.POST.get("delta", 0))
            p.pv_atual = max(-p.pv_maximo, min(p.pv_maximo, p.pv_atual + delta))
            p.save(update_fields=["pv_atual"])

        else:  # "set"
            raw = request.POST.get("valor", "")
            if raw != "":
                p.pv_atual = max(-p.pv_maximo, min(p.pv_maximo, int(raw)))
            tmp = request.POST.get("pv_temporario", "")
            if tmp != "":
                p.pv_temporario = max(0, int(tmp))
            p.save(update_fields=["pv_atual", "pv_temporario"])

    return redirect("combate")


@require_POST
def aplicar_descanso(request, tipo):
    p = get_current_character(request)
    if p:
        if tipo == "longo":
            p.pv_atual = p.pv_maximo
            p.pv_temporario = 0
            p.save(update_fields=["pv_atual", "pv_temporario"])
            p.recursos.all().update(usos_restantes=F("usos_totais"))
    return redirect("combate")


@require_POST
def descanso_curto_dados(request):
    """Processa os dados de cura do descanso curto e restaura +1 Fúria."""
    p = get_current_character(request)
    if p:
        dados_raw = request.POST.getlist("dado")
        con_mod = p.mod_constituicao
        total_cura = 0
        for d in dados_raw:
            try:
                val = int(d)
                if val > 0:
                    total_cura += max(1, val + con_mod)
            except (ValueError, TypeError):
                pass
        if total_cura > 0:
            p.pv_atual = min(p.pv_maximo, p.pv_atual + total_cura)
            p.save(update_fields=["pv_atual"])

        # Restaura exatamente +1 uso da Fúria (regra do bárbaro)
        furia = p.recursos.filter(nome="Fúria").first()
        if furia and furia.usos_restantes < furia.usos_totais:
            furia.usos_restantes += 1
            furia.save(update_fields=["usos_restantes"])

    return redirect("combate")


@require_POST
def usar_recurso(request, pk):
    r = get_object_or_404(RecursoDeCombate, pk=pk)
    if r.usos_restantes > 0:
        r.usos_restantes -= 1
        r.save(update_fields=["usos_restantes"])
    return redirect("combate")


@require_POST
def restaurar_recurso(request, pk):
    r = get_object_or_404(RecursoDeCombate, pk=pk)
    r.usos_restantes = r.usos_totais
    r.save(update_fields=["usos_restantes"])
    return redirect("combate")


# ── Notas de Combate ──────────────────────────────────────────────────────────

class NotaCombateCreateView(CreateView):
    model = NotaCombate
    form_class = NotaCombateForm
    template_name = "campanha/generic_form.html"
    success_url = reverse_lazy("combate")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Nova Nota de Combate"
        ctx["cancel_url"] = reverse_lazy("combate")
        return ctx

    def form_valid(self, form):
        form.instance.personagem = get_current_character(self.request)
        return super().form_valid(form)


class NotaCombateUpdateView(UpdateView):
    model = NotaCombate
    form_class = NotaCombateForm
    template_name = "campanha/generic_form.html"
    success_url = reverse_lazy("combate")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar: {self.object.titulo}"
        ctx["cancel_url"] = reverse_lazy("combate")
        return ctx


class NotaCombateDeleteView(DeleteView):
    model = NotaCombate
    template_name = "campanha/generic_confirm_delete.html"
    success_url = reverse_lazy("combate")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = reverse_lazy("combate")
        return ctx


# ── Itens de Inventário ───────────────────────────────────────────────────────

class ItemListView(ListView):
    model = ItemInventario
    template_name = "campanha/item_list.html"

    def get_queryset(self):
        return ItemInventario.objects.filter(personagem=get_current_character(self.request))


class ItemCreateView(CreateView):
    model = ItemInventario
    form_class = ItemInventarioForm
    template_name = "campanha/generic_form.html"
    success_url = reverse_lazy("item_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Novo Item"
        ctx["cancel_url"] = reverse_lazy("item_list")
        return ctx

    def form_valid(self, form):
        form.instance.personagem = get_current_character(self.request)
        return super().form_valid(form)


class ItemUpdateView(UpdateView):
    model = ItemInventario
    form_class = ItemInventarioForm
    template_name = "campanha/generic_form.html"
    success_url = reverse_lazy("item_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar: {self.object.nome}"
        ctx["cancel_url"] = reverse_lazy("item_list")
        return ctx


class ItemDeleteView(DeleteView):
    model = ItemInventario
    template_name = "campanha/generic_confirm_delete.html"
    success_url = reverse_lazy("item_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = reverse_lazy("item_list")
        return ctx


# ── Recursos de Combate ───────────────────────────────────────────────────────

class RecursoListView(ListView):
    model = RecursoDeCombate
    template_name = "campanha/recurso_list.html"

    def get_queryset(self):
        return RecursoDeCombate.objects.filter(personagem=get_current_character(self.request))


class RecursoCreateView(CreateView):
    model = RecursoDeCombate
    form_class = RecursoDeCombateForm
    template_name = "campanha/generic_form.html"
    success_url = reverse_lazy("recurso_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Novo Recurso de Combate"
        ctx["cancel_url"] = reverse_lazy("recurso_list")
        return ctx

    def form_valid(self, form):
        form.instance.personagem = get_current_character(self.request)
        return super().form_valid(form)


class RecursoUpdateView(UpdateView):
    model = RecursoDeCombate
    form_class = RecursoDeCombateForm
    template_name = "campanha/generic_form.html"
    success_url = reverse_lazy("recurso_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar: {self.object.nome}"
        ctx["cancel_url"] = reverse_lazy("recurso_list")
        return ctx


class RecursoDeleteView(DeleteView):
    model = RecursoDeCombate
    template_name = "campanha/generic_confirm_delete.html"
    success_url = reverse_lazy("recurso_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = reverse_lazy("recurso_list")
        return ctx


# ── Locais ────────────────────────────────────────────────────────────────────

class LocalListView(ListView):
    model = Local
    template_name = "campanha/local_list.html"


class LocalDetailView(DetailView):
    model = Local
    template_name = "campanha/local_detail.html"


class LocalCreateView(CreateView):
    model = Local
    form_class = LocalForm
    template_name = "campanha/generic_form.html"
    success_url = reverse_lazy("local_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Novo Local"
        ctx["cancel_url"] = reverse_lazy("local_list")
        return ctx


class LocalUpdateView(UpdateView):
    model = Local
    form_class = LocalForm
    template_name = "campanha/generic_form.html"

    def get_success_url(self):
        return reverse_lazy("local_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar: {self.object.nome}"
        ctx["cancel_url"] = reverse_lazy("local_detail", kwargs={"pk": self.object.pk})
        return ctx


class LocalDeleteView(DeleteView):
    model = Local
    template_name = "campanha/generic_confirm_delete.html"
    success_url = reverse_lazy("local_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = reverse_lazy("local_list")
        return ctx


# ── NPCs ──────────────────────────────────────────────────────────────────────

class NPCListView(ListView):
    model = NPC
    template_name = "campanha/npc_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["locais"] = Local.objects.all()
        return ctx


class NPCDetailView(DetailView):
    model = NPC
    template_name = "campanha/npc_detail.html"


class NPCCreateView(CreateView):
    model = NPC
    form_class = NPCForm
    template_name = "campanha/generic_form.html"
    success_url = reverse_lazy("npc_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Novo NPC"
        ctx["cancel_url"] = reverse_lazy("npc_list")
        return ctx


class NPCUpdateView(UpdateView):
    model = NPC
    form_class = NPCForm
    template_name = "campanha/generic_form.html"

    def get_success_url(self):
        return reverse_lazy("npc_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar: {self.object.nome}"
        ctx["cancel_url"] = reverse_lazy("npc_detail", kwargs={"pk": self.object.pk})
        return ctx


class NPCDeleteView(DeleteView):
    model = NPC
    template_name = "campanha/generic_confirm_delete.html"
    success_url = reverse_lazy("npc_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = reverse_lazy("npc_list")
        return ctx


# ── Missões ───────────────────────────────────────────────────────────────────

class MissaoListView(ListView):
    model = Missao
    template_name = "campanha/missao_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ativas = Missao.objects.filter(status="ativa")
        ctx["colunas"] = [
            {
                "tipo": "principal",
                "label": "Missão Principal",
                "icon": "bi-star-fill",
                "missoes": ativas.filter(tipo="principal"),
            },
            {
                "tipo": "contrato",
                "label": "Contratos",
                "icon": "bi-file-earmark-text-fill",
                "missoes": ativas.filter(tipo="contrato"),
            },
            {
                "tipo": "secundaria",
                "label": "Secundárias",
                "icon": "bi-flag-fill",
                "missoes": ativas.filter(tipo="secundaria"),
            },
        ]
        ctx["concluidas"] = Missao.objects.filter(status="concluida")
        return ctx


class MissaoDetailView(DetailView):
    model = Missao
    template_name = "campanha/missao_detail.html"


class MissaoCreateView(CreateView):
    model = Missao
    form_class = MissaoForm
    template_name = "campanha/generic_form.html"
    success_url = reverse_lazy("missao_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Nova Missão"
        ctx["cancel_url"] = reverse_lazy("missao_list")
        return ctx


class MissaoUpdateView(UpdateView):
    model = Missao
    form_class = MissaoForm
    template_name = "campanha/generic_form.html"

    def get_success_url(self):
        return reverse_lazy("missao_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar: {self.object.titulo}"
        ctx["cancel_url"] = reverse_lazy("missao_detail", kwargs={"pk": self.object.pk})
        return ctx


class MissaoDeleteView(DeleteView):
    model = Missao
    template_name = "campanha/generic_confirm_delete.html"
    success_url = reverse_lazy("missao_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = reverse_lazy("missao_list")
        return ctx


@require_POST
def concluir_missao(request, pk):
    missao = get_object_or_404(Missao, pk=pk)
    resultado = request.POST.get("resultado", "")
    missao.status = "concluida"
    if resultado:
        missao.resultado = resultado
    missao.save()
    return redirect("missao_list")


# ── Sessões ───────────────────────────────────────────────────────────────────

class SessaoListView(ListView):
    model = ResumoSessao
    template_name = "campanha/sessao_list.html"


class SessaoDetailView(DetailView):
    model = ResumoSessao
    template_name = "campanha/sessao_detail.html"


class SessaoCreateView(CreateView):
    model = ResumoSessao
    form_class = ResumoSessaoForm
    template_name = "campanha/generic_form.html"
    success_url = reverse_lazy("sessao_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Nova Sessão"
        ctx["cancel_url"] = reverse_lazy("sessao_list")
        return ctx


class SessaoUpdateView(UpdateView):
    model = ResumoSessao
    form_class = ResumoSessaoForm
    template_name = "campanha/generic_form.html"

    def get_success_url(self):
        return reverse_lazy("sessao_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar: {self.object}"
        ctx["cancel_url"] = reverse_lazy("sessao_detail", kwargs={"pk": self.object.pk})
        return ctx


class SessaoDeleteView(DeleteView):
    model = ResumoSessao
    template_name = "campanha/generic_confirm_delete.html"
    success_url = reverse_lazy("sessao_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = reverse_lazy("sessao_list")
        return ctx


# ── Informações Importantes ───────────────────────────────────────────────────

class InfoCreateView(CreateView):
    model = InformacaoImportante
    form_class = InformacaoImportanteForm
    template_name = "campanha/generic_form.html"
    success_url = reverse_lazy("dashboard")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Nova Informação"
        ctx["cancel_url"] = reverse_lazy("dashboard")
        return ctx


class InfoDeleteView(DeleteView):
    model = InformacaoImportante
    template_name = "campanha/generic_confirm_delete.html"
    success_url = reverse_lazy("dashboard")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = reverse_lazy("dashboard")
        return ctx
