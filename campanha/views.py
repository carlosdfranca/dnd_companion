import json

from django.core.exceptions import ValidationError
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.views.decorators.http import require_POST
from django.urls import reverse_lazy

from . import constants, regras
from .models import (
    Personagem, RecursoDeCombate, Equipamento, Pocao,
    ComponenteAlquimico, BaseAlquimica, ComponenteCriatura,
    Local, NPC, Missao, ResumoSessao, InformacaoImportante, NotaCombate,
)
from .forms import (
    PersonagemForm, PericiaFormSet, SalvaguardaFormSet, EssenciaFormSet,
    RecursoDeCombateForm, ItemInventarioForm, EfeitoItemFormSet, MoedasForm,
    ComponenteAlquimicoForm, BaseAlquimicaForm, ComponenteCriaturaForm,
    LocalForm, NPCForm, MissaoForm, ResumoSessaoForm, InformacaoImportanteForm,
    NotaCombateForm,
)
from .utils import get_current_character


def _flash_avisos(request, avisos, tipo="info"):
    """Fila de avisos na sessão, mostrada uma vez na próxima renderização
    COMPLETA de /itens/ — mesmo padrão de flash usado para `furia_fx` em
    central_combate. Usada pela resposta não-AJAX das actions de item e por
    `pocao_usar` (que não tem contraparte AJAX)."""
    if not avisos:
        return
    fila = request.session.get("item_avisos", [])
    fila.extend({"texto": a, "tipo": tipo} for a in avisos)
    request.session["item_avisos"] = fila


def _flash_avisos_dicts(request, avisos_dicts):
    """Como `_flash_avisos`, mas recebe uma lista já no formato
    `{"texto":, "tipo":}` — usada quando um lote pode ter tipos mistos
    (não é o caso hoje, mas mantém a sessão e a resposta AJAX no mesmo formato)."""
    if not avisos_dicts:
        return
    fila = request.session.get("item_avisos", [])
    fila.extend(avisos_dicts)
    request.session["item_avisos"] = fila


def _avisos_dicts(textos, tipo="info"):
    return [{"texto": t, "tipo": tipo} for t in (textos or [])]


def _texto_validation_error(exc):
    return "; ".join(getattr(exc, "messages", None) or [str(exc)])


def _contexto_inventario(personagem):
    """Contexto dos blocos de Equipamento/Mochila do inventário — usado
    tanto pelo GET completo de `ItemListView` quanto pelas respostas AJAX
    das 5 actions de item (`_item_acao_resposta`), pra garantir que os dois
    produzam exatamente o mesmo HTML a partir do mesmo dicionário."""
    if personagem is None:
        return {
            "grid_slots": [
                {"slot": ident, "label": label,
                 "icone": constants.SLOT_ICONES.get(ident, ""), "ocupacao": None}
                for ident, label, _ordem in constants.SLOTS_EQUIPAMENTO
            ],
            "mochila": [],
            "slot_choices": constants.SLOT_CHOICES,
            "sintonizados": 0,
            "limite_sintonizacao": constants.LIMITE_SINTONIZACAO,
            "excedeu_sintonizacao": False,
            "carga_atual": 0, "capacidade_carga": 0,
            "percentual_carga": 0, "sobrecarregado": False,
        }

    itens = list(
        Equipamento.objects.filter(personagem=personagem).prefetch_related("efeitos")
    )

    # Mapa slot -> {"item":, "primario": bool}. Arma de duas mãos ocupa 2
    # slots (ver Equipamento.slots_ocupados) mesmo só gravando um `slot`;
    # o secundário aparece marcado como não-primário no grid.
    ocupacao = {}
    for item in itens:
        if not item.slot:
            continue
        for indice, ident in enumerate(item.slots_ocupados):
            ocupacao[ident] = {"item": item, "primario": indice == 0}

    grid_slots = [
        {"slot": ident, "label": label,
         "icone": constants.SLOT_ICONES.get(ident, ""), "ocupacao": ocupacao.get(ident)}
        for ident, label, _ordem in constants.SLOTS_EQUIPAMENTO
    ]

    return {
        "grid_slots": grid_slots,
        "mochila": [i for i in itens if not i.slot],
        "slot_choices": constants.SLOT_CHOICES,
        "sintonizados": personagem.sintonizados_count,
        "limite_sintonizacao": constants.LIMITE_SINTONIZACAO,
        "excedeu_sintonizacao": personagem.excedeu_sintonizacao,
        "carga_atual": personagem.carga_atual,
        "capacidade_carga": personagem.capacidade_carga,
        "percentual_carga": personagem.percentual_carga,
        "sobrecarregado": personagem.sobrecarregado,
    }


def _item_acao_resposta(request, personagem, avisos_dicts):
    """Resposta comum das 5 actions de item (equipar/desequipar/sintonizar/
    dessintonizar/empunhadura).

    Fora de AJAX: flasheia os avisos na sessão e redireciona — exatamente
    como sempre foi.

    Em AJAX (`X-Requested-With`): devolve os blocos de Equipamento/Mochila
    já renderizados a partir de `_contexto_inventario`, com os avisos NO
    CORPO da resposta — nunca gravados na sessão nesse branch, senão
    reapareceriam velhos da próxima vez que a página carregasse de verdade
    (a sessão só é esvaziada por `ItemListView.get_context_data`).
    """
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        _flash_avisos_dicts(request, avisos_dicts)
        return redirect("item_list")

    ctx = _contexto_inventario(personagem)
    return JsonResponse({
        "ok": True,
        "equip_html": render_to_string("campanha/partials/_equip_body.html", ctx, request=request),
        "mochila_html": render_to_string("campanha/partials/_mochila_body.html", ctx, request=request),
        "avisos_html": render_to_string(
            "campanha/partials/_inv_avisos.html", {"avisos": avisos_dicts}, request=request
        ),
    })


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


def _pericia_groups(pericia_fs):
    """Agrupa os forms de perícia por atributo regente, na ordem de ATRIBUTOS."""
    from . import constants
    por_atributo = {attr: [] for attr, _, _ in constants.ATRIBUTOS}
    for pform in pericia_fs.forms:
        por_atributo.setdefault(pform.instance.atributo, []).append(pform)
    grupos = []
    for attr, label, abrev in constants.ATRIBUTOS:
        forms_do_grupo = sorted(por_atributo.get(attr, []), key=lambda f: f.instance.rotulo)
        if forms_do_grupo:
            grupos.append({"attr": attr, "label": label, "abrev": abrev, "forms": forms_do_grupo})
    return grupos


class FichaEditView(View):
    template_name = "campanha/ficha_editar.html"

    def _get_personagem(self):
        return get_current_character(self.request)

    def _context(self, p, form, pericia_fs, salvaguarda_fs):
        salvaguarda_forms = sorted(salvaguarda_fs.forms, key=lambda f: f.instance.ordem)
        return {
            "form": form,
            "pericia_fs": pericia_fs,
            "salvaguarda_fs": salvaguarda_fs,
            "pericia_groups": _pericia_groups(pericia_fs),
            "salvaguarda_forms": salvaguarda_forms,
            "personagem": p,
        }

    def get(self, request):
        p = self._get_personagem()
        pericias_fs = PericiaFormSet(instance=p, prefix="pericias")
        salvaguardas_fs = SalvaguardaFormSet(instance=p, prefix="salvaguardas")
        return render(request, self.template_name, self._context(
            p, PersonagemForm(instance=p), pericias_fs, salvaguardas_fs,
        ))

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
        return render(request, self.template_name, self._context(
            p, form, pericia_fs, salvaguarda_fs,
        ))


# ── Central de Combate ────────────────────────────────────────────────────────

def _pv_pct(personagem):
    """Percentual de PV atual sobre o máximo, limitado a [0, 100]."""
    if not personagem or not personagem.pv_maximo:
        return 0
    return max(0, min(100, round(personagem.pv_atual * 100 / personagem.pv_maximo)))


def _recursos_com_pips(personagem):
    """Lista de recursos de combate com os pips (usado/disponível) já montados."""
    recursos_com_pips = []
    for r in personagem.recursos.all():
        pips = [i < r.usos_restantes for i in range(r.usos_totais)]
        recursos_com_pips.append({"recurso": r, "pips": pips})
    return recursos_com_pips


def central_combate(request):
    personagem = get_current_character(request)
    pv_pct = 0
    recursos_com_pips = []
    itens_equipados = []
    magicos_equipados = 0
    dado_range = range(0)
    ataques = []
    notas_combate = []
    furia_fx = request.session.pop("furia_fx", None)
    if personagem:
        pv_pct = _pv_pct(personagem)
        recursos_com_pips = _recursos_com_pips(personagem)
        itens_equipados = personagem.itens.filter(tipo="equipado")
        # Conta sintonização de verdade (Equipamento.sintonizado), não mais o
        # proxy antigo `magico` — mesma regra usada em ItemListView agora.
        magicos_equipados = personagem.sintonizados_count
        dado_range = range(personagem.nivel)
        notas_combate = personagem.notas_combate.all()
        ataques = regras.ataques_do_personagem(personagem)
    return render(request, "campanha/central_combate.html", {
        "personagem": personagem,
        "pv_pct": pv_pct,
        "recursos_com_pips": recursos_com_pips,
        "itens_equipados": itens_equipados,
        "magicos_equipados": magicos_equipados,
        "limite_magicos": constants.LIMITE_SINTONIZACAO,
        "excedeu_magicos": magicos_equipados > constants.LIMITE_SINTONIZACAO,
        "dado_range": dado_range,
        "notas_combate": notas_combate,
        "ataques": ataques,
        "furia_fx": furia_fx,
    })


@require_POST
def atualizar_pv(request):
    p = get_current_character(request)
    acao = request.POST.get("acao", "set")
    aplicado = 0

    if p:
        if acao == "dano":
            # Temp HP absorve primeiro; dano negativo ignorado
            dano = max(0, int(request.POST.get("valor", 0)))
            if p.furia_ativa and request.POST.get("fisico"):
                # Fúria: dano cortante/perfurante/concussão é reduzido à metade (arred. p/ cima)
                dano = (dano + 1) // 2
            if p.pv_temporario > 0:
                absorvido = min(dano, p.pv_temporario)
                p.pv_temporario -= absorvido
                dano -= absorvido
            pv_antes = p.pv_atual
            p.pv_atual = max(-p.pv_maximo, p.pv_atual - dano)
            aplicado = pv_antes - p.pv_atual
            p.save(update_fields=["pv_atual", "pv_temporario"])

        elif acao == "cura":
            cura = max(0, int(request.POST.get("valor", 0)))
            pv_antes = p.pv_atual
            p.pv_atual = min(p.pv_maximo, p.pv_atual + cura)
            aplicado = p.pv_atual - pv_antes
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

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        if not p:
            return JsonResponse({"ok": False}, status=404)
        return JsonResponse({
            "ok": True,
            "tipo": acao,
            "aplicado": aplicado,
            "pv_atual": p.pv_atual,
            "pv_maximo": p.pv_maximo,
            "pv_temporario": p.pv_temporario,
            "pv_pct": _pv_pct(p),
        })

    return redirect("combate")


def _descanso_ajax_response(request, p, tipo, aplicado=0, ataques_html=True):
    """Payload comum devolvido pelas views de descanso quando a requisição é AJAX."""
    payload = {
        "ok": True,
        "tipo": tipo,
        "aplicado": aplicado,
        "pv_atual": p.pv_atual,
        "pv_maximo": p.pv_maximo,
        "pv_temporario": p.pv_temporario,
        "pv_pct": _pv_pct(p),
        "furia_ativa": p.furia_ativa,
        "recursos_html": render_to_string(
            "campanha/partials/_recursos_body.html",
            {"recursos_com_pips": _recursos_com_pips(p), "personagem": p},
            request=request,
        ),
    }
    if ataques_html:
        payload["ataques_html"] = render_to_string(
            "campanha/partials/_ataques_body.html",
            {"ataques": regras.ataques_do_personagem(p), "personagem": p},
            request=request,
        )
    return JsonResponse(payload)


@require_POST
def aplicar_descanso(request, tipo):
    p = get_current_character(request)
    if p:
        if tipo == "longo":
            p.pv_atual = p.pv_maximo
            p.pv_temporario = 0
            p.furia_ativa = False
            p.save(update_fields=["pv_atual", "pv_temporario", "furia_ativa"])
            p.recursos.all().update(usos_restantes=F("usos_totais"))

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        if not p:
            return JsonResponse({"ok": False}, status=404)
        return _descanso_ajax_response(request, p, "longo")

    return redirect("combate")


@require_POST
def descanso_curto_dados(request):
    """Processa os dados de cura do descanso curto e restaura +1 Fúria."""
    p = get_current_character(request)
    total_cura = 0
    if p:
        dados_raw = request.POST.getlist("dado")
        con_mod = p.mod_constituicao
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

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        if not p:
            return JsonResponse({"ok": False}, status=404)
        return _descanso_ajax_response(request, p, "curto", aplicado=total_cura, ataques_html=False)

    return redirect("combate")


@require_POST
def usar_recurso(request, pk):
    r = get_object_or_404(RecursoDeCombate, pk=pk)
    if r.usos_restantes > 0:
        r.usos_restantes -= 1
        r.save(update_fields=["usos_restantes"])
        if r.nome == "Fúria":
            p = r.personagem
            p.furia_ativa = True
            p.pv_temporario = max(p.pv_temporario, p.nivel)
            p.save(update_fields=["furia_ativa", "pv_temporario"])
            request.session["furia_fx"] = 1
    return redirect("combate")


@require_POST
def restaurar_recurso(request, pk):
    r = get_object_or_404(RecursoDeCombate, pk=pk)
    r.usos_restantes = r.usos_totais
    r.save(update_fields=["usos_restantes"])
    return redirect("combate")


@require_POST
def encerrar_furia(request):
    """Desativa o estado de Fúria sem alterar os usos restantes do recurso."""
    p = get_current_character(request)
    if p:
        p.furia_ativa = False
        p.save(update_fields=["furia_ativa"])
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
    model = Equipamento
    template_name = "campanha/item_list.html"

    def get_queryset(self):
        return (
            Equipamento.objects
            .filter(personagem=get_current_character(self.request))
            .prefetch_related("efeitos")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        p = get_current_character(self.request)

        essencia_fs = EssenciaFormSet(instance=p, prefix="essencias") if p else None
        essencia_forms = sorted(essencia_fs.forms, key=lambda f: f.instance.ordem) if essencia_fs else []

        ctx.update(_contexto_inventario(p))
        ctx.update({
            "personagem": p,
            "moedas_form": MoedasForm(instance=p),
            "pocoes": p.pocoes.all() if p else [],
            "componentes_alquimicos": p.componentes_alquimicos.all() if p else [],
            "bases_alquimicas": p.bases_alquimicas.all() if p else [],
            "componentes_criatura": p.componentes_criatura.all() if p else [],
            "essencia_fs": essencia_fs,
            "essencia_forms": essencia_forms,
            "empunhadura_choices": constants.EMPUNHADURA_CHOICES,
            "avisos": self.request.session.pop("item_avisos", []),
        })
        return ctx


@require_POST
def atualizar_moedas(request):
    p = get_current_character(request)
    if p:
        form = MoedasForm(request.POST, instance=p)
        if form.is_valid():
            form.save()
    return redirect("item_list")


@require_POST
def item_equipar(request, pk):
    equipamento = get_object_or_404(Equipamento, pk=pk)
    slot = request.POST.get("slot") or None
    try:
        avisos = _avisos_dicts(regras.equipar(equipamento, slot_alvo=slot))
    except ValidationError as exc:
        avisos = _avisos_dicts([_texto_validation_error(exc)], tipo="erro")
    return _item_acao_resposta(request, equipamento.personagem, avisos)


@require_POST
def item_desequipar(request, pk):
    equipamento = get_object_or_404(Equipamento, pk=pk)
    regras.desequipar(equipamento)
    return _item_acao_resposta(request, equipamento.personagem, [])


@require_POST
def item_sintonizar(request, pk):
    equipamento = get_object_or_404(Equipamento, pk=pk)
    try:
        regras.sintonizar(equipamento)
        avisos = []
    except ValidationError as exc:
        avisos = _avisos_dicts([_texto_validation_error(exc)], tipo="erro")
    return _item_acao_resposta(request, equipamento.personagem, avisos)


@require_POST
def item_dessintonizar(request, pk):
    equipamento = get_object_or_404(Equipamento, pk=pk)
    regras.dessintonizar(equipamento)
    return _item_acao_resposta(request, equipamento.personagem, [])


@require_POST
def item_empunhadura(request, pk):
    equipamento = get_object_or_404(Equipamento, pk=pk)
    nova = request.POST.get("empunhadura")
    try:
        avisos = _avisos_dicts(regras.trocar_empunhadura(equipamento, nova))
    except ValidationError as exc:
        avisos = _avisos_dicts([_texto_validation_error(exc)], tipo="erro")
    return _item_acao_resposta(request, equipamento.personagem, avisos)


@require_POST
def pocao_usar(request, pk):
    pocao = get_object_or_404(Pocao, pk=pk)
    avisos = regras.aplicar_pocao(pocao)
    _flash_avisos(request, avisos)
    return redirect("item_list")


class ItemCreateView(CreateView):
    model = Equipamento
    form_class = ItemInventarioForm
    template_name = "campanha/generic_form.html"
    success_url = reverse_lazy("item_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Novo Item"
        ctx["cancel_url"] = reverse_lazy("item_list")
        ctx["formset_titulo"] = "Efeitos do item"
        if "formset" not in ctx:
            if self.request.method == "POST":
                ctx["formset"] = EfeitoItemFormSet(self.request.POST, instance=self.object)
            else:
                ctx["formset"] = EfeitoItemFormSet(instance=self.object)
        return ctx

    def form_valid(self, form):
        form.instance.personagem = get_current_character(self.request)
        formset = self.get_context_data()["formset"]
        if not formset.is_valid():
            return self.render_to_response(self.get_context_data(form=form))
        response = super().form_valid(form)  # grava form, define self.object
        formset.instance = self.object
        formset.save()
        return response


class ItemUpdateView(UpdateView):
    model = Equipamento
    form_class = ItemInventarioForm
    template_name = "campanha/generic_form.html"
    success_url = reverse_lazy("item_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar: {self.object.nome}"
        ctx["cancel_url"] = reverse_lazy("item_list")
        ctx["formset_titulo"] = "Efeitos do item"
        if "formset" not in ctx:
            if self.request.method == "POST":
                ctx["formset"] = EfeitoItemFormSet(self.request.POST, instance=self.object)
            else:
                ctx["formset"] = EfeitoItemFormSet(instance=self.object)
        return ctx

    def form_valid(self, form):
        formset = self.get_context_data()["formset"]
        if not formset.is_valid():
            return self.render_to_response(self.get_context_data(form=form))
        response = super().form_valid(form)
        formset.instance = self.object
        formset.save()
        return response


class ItemDeleteView(DeleteView):
    model = Equipamento
    template_name = "campanha/generic_confirm_delete.html"
    success_url = reverse_lazy("item_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = reverse_lazy("item_list")
        return ctx


# ── Alquimia ──────────────────────────────────────────────────────────────────
# CRUD simples — armazenamento puro, sem slot, sem efeito mecânico, sem
# formset de efeitos (ao contrário de Equipamento/EfeitoItem).

class ComponenteAlquimicoCreateView(CreateView):
    model = ComponenteAlquimico
    form_class = ComponenteAlquimicoForm
    template_name = "campanha/generic_form.html"
    success_url = reverse_lazy("item_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Novo Componente Alquímico"
        ctx["cancel_url"] = reverse_lazy("item_list")
        return ctx

    def form_valid(self, form):
        form.instance.personagem = get_current_character(self.request)
        return super().form_valid(form)


class ComponenteAlquimicoUpdateView(UpdateView):
    model = ComponenteAlquimico
    form_class = ComponenteAlquimicoForm
    template_name = "campanha/generic_form.html"
    success_url = reverse_lazy("item_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar: {self.object.nome}"
        ctx["cancel_url"] = reverse_lazy("item_list")
        return ctx


class ComponenteAlquimicoDeleteView(DeleteView):
    model = ComponenteAlquimico
    template_name = "campanha/generic_confirm_delete.html"
    success_url = reverse_lazy("item_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = reverse_lazy("item_list")
        return ctx


class BaseAlquimicaCreateView(CreateView):
    model = BaseAlquimica
    form_class = BaseAlquimicaForm
    template_name = "campanha/generic_form.html"
    success_url = reverse_lazy("item_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Nova Base Alquímica"
        ctx["cancel_url"] = reverse_lazy("item_list")
        return ctx

    def form_valid(self, form):
        form.instance.personagem = get_current_character(self.request)
        return super().form_valid(form)


class BaseAlquimicaUpdateView(UpdateView):
    model = BaseAlquimica
    form_class = BaseAlquimicaForm
    template_name = "campanha/generic_form.html"
    success_url = reverse_lazy("item_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar: {self.object.nome}"
        ctx["cancel_url"] = reverse_lazy("item_list")
        return ctx


class BaseAlquimicaDeleteView(DeleteView):
    model = BaseAlquimica
    template_name = "campanha/generic_confirm_delete.html"
    success_url = reverse_lazy("item_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = reverse_lazy("item_list")
        return ctx


# ── Harvesting ────────────────────────────────────────────────────────────────
# Essência é editada como formset (mesmo padrão de PericiaFormSet/
# SalvaguardaFormSet), com endpoint POST próprio — mesmo estilo de
# MoedasForm/atualizar_moedas, um widget pequeno embutido em /itens/.

@require_POST
def essencia_atualizar(request):
    p = get_current_character(request)
    if p:
        formset = EssenciaFormSet(request.POST, instance=p, prefix="essencias")
        if formset.is_valid():
            formset.save()
    return redirect("item_list")


class ComponenteCriaturaCreateView(CreateView):
    model = ComponenteCriatura
    form_class = ComponenteCriaturaForm
    template_name = "campanha/generic_form.html"
    success_url = reverse_lazy("item_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Novo Componente de Criatura"
        ctx["cancel_url"] = reverse_lazy("item_list")
        return ctx

    def form_valid(self, form):
        form.instance.personagem = get_current_character(self.request)
        return super().form_valid(form)


class ComponenteCriaturaUpdateView(UpdateView):
    model = ComponenteCriatura
    form_class = ComponenteCriaturaForm
    template_name = "campanha/generic_form.html"
    success_url = reverse_lazy("item_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar: {self.object.nome}"
        ctx["cancel_url"] = reverse_lazy("item_list")
        return ctx


class ComponenteCriaturaDeleteView(DeleteView):
    model = ComponenteCriatura
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


# ── Ataques / Dano ────────────────────────────────────────────────────────────
# CRUD de Ataque removido junto com o model (ver models.py). A tela de gestão
# de ataques (listar/criar/editar/excluir armas cadastradas à mão) volta como
# TemplateView somativa das armas equipadas quando a fase de UI do sistema de
# itens estruturado for autorizada — ver campanha/regras.py.


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


@require_POST
def reordenar_missoes(request):
    """Recebe a nova ordem (lista de pks) de uma coluna do kanban e persiste em `ordem`."""
    try:
        pks = json.loads(request.body).get("ordem", [])
    except (ValueError, TypeError):
        return JsonResponse({"ok": False}, status=400)
    for indice, pk in enumerate(pks):
        Missao.objects.filter(pk=pk).update(ordem=indice)
    return JsonResponse({"ok": True})


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
        ctx["full_width"] = True
        ctx["inline_fields"] = ["numero", "titulo", "data"]
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
        ctx["full_width"] = True
        ctx["inline_fields"] = ["numero", "titulo", "data"]
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
