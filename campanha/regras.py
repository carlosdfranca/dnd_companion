"""
Motor de cálculo de efeitos de equipamento.

Funções puras — nada aqui importa `campanha.models` no nível do módulo (evita
import circular, já que `models.py` importa este módulo) nem faz query além
das duas explícitas em `coletar_efeitos`. Os models expõem o resultado dessas
funções como `@property`/`@cached_property` para os templates continuarem
lendo `personagem.ca`, `salvaguarda.modificador_total` etc. sem saber que
existe um motor por trás.

Ver campanha/constants.py para as tabelas de regra (ALVOS_EFEITO, TIPOS_BONUS,
ESTILOS_CA, CATEGORIAS_ARMADURA...) que este módulo consome.
"""

import random
from collections import namedtuple
from dataclasses import dataclass
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from . import constants

# itens   -> lista de Equipamento com efeitos_habilitados == True (equipado E,
#            se exige sintonização, sintonizado)
# efeitos -> lista achatada de (equipamento, EfeitoItem) já filtrada pelo gate
ContextoEfeitos = namedtuple("ContextoEfeitos", "itens efeitos")

_CONTEXTO_VAZIO = ContextoEfeitos([], [])


def coletar_efeitos(personagem):
    """Reúne os equipamentos ativos e seus efeitos em 2 queries.

    Chamado uma vez por request via `Personagem.efeitos_ativos`
    (`@cached_property`) — todo consumidor (CA, salvaguardas, perícias,
    iniciativa, ataques) reaproveita o mesmo bundle.
    """
    if personagem is None or personagem.pk is None:
        return _CONTEXTO_VAZIO
    itens = [
        i for i in personagem.itens.exclude(slot__isnull=True).prefetch_related("efeitos")
        if i.efeitos_habilitados
    ]
    efeitos = [(item, ef) for item in itens for ef in item.efeitos.all()]
    return ContextoEfeitos(itens, efeitos)


def bonus_para(ctx, escopo, chave="", incluir_condicionais=False):
    """Soma os bônus numéricos ativos para um (escopo, chave).

    Empilhamento (regra 5e): bônus SEM tipo (`tipo_bonus == ""`) sempre
    somam entre si; bônus com o MESMO tipo nomeado NÃO somam — vale o maior;
    tipos diferentes somam entre si. Efeitos com `condicao` preenchida são
    situacionais e ficam de fora da soma, a menos que `incluir_condicionais`
    seja True (usado só para listar, nunca para somar CA/saves de verdade).
    """
    sem_tipo = 0
    por_tipo = {}
    for _item, ef in ctx.efeitos:
        if ef.categoria != "numerico":
            continue
        if ef.condicao and not incluir_condicionais:
            continue
        _, esc, ch = constants.ALVO_EFEITO_MAP.get(ef.alvo, ("", "", ""))
        if esc != escopo:
            continue
        if ch and ch != chave:
            continue  # ch == "" casa com todo o escopo; ch específico exige bater
        if ef.tipo_bonus:
            anterior = por_tipo.get(ef.tipo_bonus)
            por_tipo[ef.tipo_bonus] = ef.valor if anterior is None else max(anterior, ef.valor)
        else:
            sem_tipo += ef.valor
    return sem_tipo + sum(por_tipo.values())


def ca_base(personagem, ctx):
    """CA base: armadura vestida vence a fórmula de classe (Defesa sem Armadura
    para de valer quando se veste armadura — modelado corretamente por essa
    ordem de prioridade, sem precisar de um `if` extra)."""
    mod_des = personagem.mod_destreza
    armadura = next(
        (i for i in ctx.itens if i.categoria_armadura and i.ca_base_armadura is not None),
        None,
    )
    if armadura:
        _, limite = constants.CATEGORIA_ARMADURA_MAP.get(armadura.categoria_armadura, ("", None))
        des = mod_des if limite is None else min(mod_des, limite)
        return armadura.ca_base_armadura + des
    _, base, extra = constants.ESTILO_CA_MAP.get(personagem.estilo_ca, ("", 10, ""))
    total = base + mod_des
    if extra:
        total += personagem.modificador(extra)
    return total


def ca_calculada(personagem):
    ctx = personagem.efeitos_ativos
    return ca_base(personagem, ctx) + bonus_para(ctx, "ca")


def detalhar_ca(personagem):
    """[(rótulo, valor)] com a composição da CA — base + cada item que contribui."""
    ctx = personagem.efeitos_ativos
    partes = [("Base", ca_base(personagem, ctx))]
    for item, ef in ctx.efeitos:
        if ef.categoria != "numerico" or ef.condicao:
            continue
        _, esc, _ch = constants.ALVO_EFEITO_MAP.get(ef.alvo, ("", "", ""))
        if esc == "ca":
            partes.append((item.nome, ef.valor))
    return partes


@dataclass(frozen=True)
class AtaqueCalculado:
    """Ataque derivado de uma arma equipada — nunca armazenado (ver models.py,
    o model Ataque foi removido para não duplicar esta mesma informação)."""

    nome: str
    bonus_ataque: int
    formula_dano: str
    formula_dano_furia: str
    tipo_dano: str
    empunhadura_label: str
    versatil: bool
    propriedades: str


def _fmt_bonus(valor):
    if valor == 0:
        return ""
    return f" +{valor}" if valor > 0 else f" −{abs(valor)}"


def ataques_do_personagem(personagem):
    """Lista de AtaqueCalculado a partir das armas equipadas (dano_qtd_dados > 0)."""
    ctx = personagem.efeitos_ativos
    resultado = []
    for item in ctx.itens:
        if item.dano_qtd_dados <= 0:
            continue
        mod = personagem.modificador(item.atributo_ataque)
        bonus_ataque = mod + bonus_para(ctx, "ataque")
        if item.proficiente:
            bonus_ataque += personagem.bonus_proficiencia
        dado = item.dado_dano
        bonus_dano = mod + bonus_para(ctx, "dano")
        formula_dano = f"{dado}{_fmt_bonus(bonus_dano)}"
        formula_dano_furia = f"{dado}{_fmt_bonus(bonus_dano + personagem.bonus_dano_furia)}"
        empunhadura_label = dict(constants.EMPUNHADURA_CHOICES).get(item.empunhadura, "")
        tipo_dano_label = constants.TIPO_DANO_MAP.get(item.tipo_dano, ("",))[0]
        resultado.append(AtaqueCalculado(
            nome=item.nome,
            bonus_ataque=bonus_ataque,
            formula_dano=formula_dano,
            formula_dano_furia=formula_dano_furia,
            tipo_dano=tipo_dano_label,
            empunhadura_label=empunhadura_label,
            versatil=item.versatil,
            propriedades=item.propriedades_texto,
        ))
    return resultado


def carga_total(personagem):
    """Soma de peso × quantidade de todo o inventário do personagem.

    Percorre todo subsistema que herda `ItemBase` (tem `peso`): Equipamento,
    Pocao, ComponenteAlquimico, BaseAlquimica, ComponenteCriatura. `Essencia`
    fica de fora de propósito — não herda ItemBase (não tem forma física,
    é um contador mágico abstrato), então não tem `peso` para somar.
    """
    total = 0
    for relacao in (
        "itens", "pocoes", "componentes_alquimicos", "bases_alquimicas",
        "componentes_criatura",
    ):
        for item in getattr(personagem, relacao).all():
            total += item.peso * item.quantidade
    return total


def capacidade_carga(personagem):
    """Capacidade de carga em kg (5e pt-br: Força × 7,5 kg).

    Decimal, não float — `peso` é DecimalField e `carga_total` retorna
    Decimal; misturar os dois tipos numa divisão levanta TypeError.
    """
    return personagem.forca * Decimal(str(constants.MULTIPLICADOR_CAPACIDADE_KG))


# ─────────────────────────────────────────────────────────────────────────────
# Equipar / desequipar / sintonizar
#
# `equipamento` chega como instância viva do model — usamos `type(equipamento)`
# em vez de importar `Equipamento` no topo do módulo para não criar um import
# circular (models.py já importa `regras` no nível do módulo).
# ─────────────────────────────────────────────────────────────────────────────

def slot_padrao_de(equipamento):
    """Slot para o qual o botão "Equipar" manda o item, se nenhum for escolhido."""
    return equipamento.slot_padrao or constants.SLOT_PADRAO_POR_CATEGORIA.get(
        equipamento.categoria, ""
    )


def _slots_ocupados_por(slot_alvo, empunhadura, duas_maos):
    if not slot_alvo:
        return set()
    if slot_alvo == "mao_principal" and (duas_maos or empunhadura == "duas"):
        return {"mao_principal", "mao_secundaria"}
    return {slot_alvo}


def _liberar_conflitos(equipamento, alvos):
    """Desequipa (ou rebaixa a uma mão) quem estiver ocupando `alvos`.

    Chamado de dentro de uma transação já aberta (`equipar`/`trocar_empunhadura`).
    Retorna a lista de avisos — o retorno é o que vira feedback visível para o
    jogador (não só log), então o texto já é a frase pronta para exibir.
    """
    Modelo = type(equipamento)
    avisos = []
    ocupantes = (
        Modelo.objects.select_for_update()
        .filter(personagem_id=equipamento.personagem_id)
        .exclude(pk=equipamento.pk)
        .exclude(slot__isnull=True)
    )
    for outro in ocupantes:
        if not (set(outro.slots_ocupados) & alvos):
            continue
        # Arma versátil segurando a mão secundária "por opção" (não por ser
        # inerentemente de duas mãos): rebaixa para uma mão em vez de
        # desequipar — equipar um escudo enquanto empunha um machado
        # versátil com duas mãos faz o machado passar a uma mão, não sumir
        # da mão principal.
        if (outro.versatil and not outro.duas_maos and outro.empunhadura == "duas"
                and outro.slot not in alvos):
            outro.empunhadura = "uma"
            outro.save(update_fields=["empunhadura"])
            avisos.append(f'"{outro.nome}" passou a ser empunhado com uma mão.')
        else:
            outro.slot = None
            outro.tipo = "mochila"
            outro.save(update_fields=["slot", "tipo"])
            avisos.append(f'"{outro.nome}" foi desequipado.')
    return avisos


@transaction.atomic
def equipar(equipamento, slot_alvo=None, empunhadura=None):
    """Equipa `equipamento` num slot, resolvendo conflitos automaticamente.

    Não mexe em sintonização — sintonizar é uma ação separada (`sintonizar`),
    fiel à regra 5e de que atualizar exige um descanso curto dedicado, não
    acontece de graça ao equipar.

    Retorna a lista de avisos sobre efeitos colaterais (item desequipado,
    arma rebaixada para uma mão).
    """
    slot_alvo = slot_alvo or slot_padrao_de(equipamento)
    if not slot_alvo:
        raise ValidationError("Este item não tem um slot de equipamento válido.")
    if slot_alvo not in constants.SLOT_MAP:
        raise ValidationError("Slot inválido.")

    # Arma de duas mãos inerente sempre ocupa a partir de mao_principal —
    # `slots_ocupados` só expande pras duas mãos quando `slot == "mao_principal"`
    # (ver models.Equipamento.slots_ocupados); pousar direto em mao_secundaria
    # (ex.: arrastada pra lá) deixaria o item marcado como ocupando só uma mão.
    if equipamento.duas_maos and slot_alvo == "mao_secundaria":
        slot_alvo = "mao_principal"

    if equipamento.duas_maos:
        empunhadura = "duas"
    else:
        empunhadura = empunhadura or equipamento.empunhadura
        if empunhadura == "duas" and not equipamento.versatil:
            empunhadura = "uma"

    alvos = _slots_ocupados_por(slot_alvo, empunhadura, equipamento.duas_maos)
    avisos = _liberar_conflitos(equipamento, alvos)

    equipamento.slot = slot_alvo
    equipamento.empunhadura = empunhadura
    equipamento.tipo = "equipado"
    equipamento.save(update_fields=["slot", "empunhadura", "tipo"])
    return avisos


def desequipar(equipamento):
    """Move o item de volta para a mochila. Sintonização NÃO cai (5e: só
    quebra por 1h sem uso ou por escolha do jogador — ver `dessintonizar`)."""
    equipamento.slot = None
    equipamento.tipo = "mochila"
    equipamento.save(update_fields=["slot", "tipo"])


def sintonizar(equipamento):
    """Sintoniza o item, respeitando o limite de constants.LIMITE_SINTONIZACAO.

    É aqui que o limite deixa de ser um contador visual e vira regra de
    verdade: só um item efetivamente `sintonizado` tem seus EfeitoItem
    contados (ver `Equipamento.efeitos_habilitados`).
    """
    if not equipamento.requer_sintonizacao:
        raise ValidationError("Este item não requer sintonização.")
    if equipamento.sintonizado:
        return
    Modelo = type(equipamento)
    with transaction.atomic():
        em_uso = (
            Modelo.objects.select_for_update()
            .filter(personagem_id=equipamento.personagem_id, sintonizado=True)
            .exclude(pk=equipamento.pk)
            .count()
        )
        if em_uso >= constants.LIMITE_SINTONIZACAO:
            raise ValidationError(
                f"Limite de {constants.LIMITE_SINTONIZACAO} itens sintonizados "
                "atingido. Quebre a sintonização de outro item primeiro."
            )
        equipamento.sintonizado = True
        equipamento.save(update_fields=["sintonizado"])


def dessintonizar(equipamento):
    equipamento.sintonizado = False
    equipamento.save(update_fields=["sintonizado"])


@transaction.atomic
def trocar_empunhadura(equipamento, nova_empunhadura):
    """Troca o modo de empunhadura (uma/duas mãos) de uma arma versátil.

    Se o item estiver equipado na mão principal e a nova empunhadura for
    "duas", libera a mão secundária como um equip normal (mesmo aviso de
    efeito colateral). Retorna a lista de avisos.
    """
    if nova_empunhadura not in dict(constants.EMPUNHADURA_CHOICES):
        raise ValidationError("Empunhadura inválida.")
    if equipamento.duas_maos:
        raise ValidationError("Esta arma é sempre empunhada com duas mãos.")
    if nova_empunhadura == "duas" and not equipamento.versatil:
        raise ValidationError("Este item não é versátil — não pode ser empunhado com duas mãos.")

    if not equipamento.slot:
        equipamento.empunhadura = nova_empunhadura
        equipamento.save(update_fields=["empunhadura"])
        return []

    alvos = _slots_ocupados_por(equipamento.slot, nova_empunhadura, equipamento.duas_maos)
    avisos = _liberar_conflitos(equipamento, alvos)
    equipamento.empunhadura = nova_empunhadura
    equipamento.save(update_fields=["empunhadura"])
    return avisos


# ─────────────────────────────────────────────────────────────────────────────
# Poções
# ─────────────────────────────────────────────────────────────────────────────

def rolar_cura(pocao):
    """(rolado, cura) — soma de `cura_qtd_dados` dados de `cura_faces` faces,
    e o mesmo valor já com `cura_bonus` somado e piso em 0."""
    rolado = sum(random.randint(1, pocao.cura_faces) for _ in range(pocao.cura_qtd_dados))
    return rolado, max(0, rolado + pocao.cura_bonus)


@transaction.atomic
def aplicar_pocao(pocao, cura_forcada=None):
    """Usa uma poção: rola a cura, soma ao PV respeitando `pv_maximo` (mesma
    fórmula de `views.atualizar_pv` ação "cura"), aplica o efeito adicional
    quando o Personagem tem onde representá-lo, decrementa a quantidade —
    removendo a poção quando chega a 0.

    `cura_forcada` pula a rolagem de dados (usado pelos testes, para não
    depender de aleatoriedade). Retorna a lista de avisos, mesma convenção
    de `equipar`/`sintonizar`/`trocar_empunhadura`.
    """
    p = pocao.personagem
    if cura_forcada is None:
        rolado, cura = rolar_cura(pocao)
    else:
        rolado, cura = cura_forcada, max(0, cura_forcada + pocao.cura_bonus)

    pv_antes = p.pv_atual
    p.pv_atual = min(p.pv_maximo, p.pv_atual + cura)
    p.save(update_fields=["pv_atual"])
    aplicado = p.pv_atual - pv_antes
    avisos = [f'{pocao.nome}: curou {aplicado} PV.']

    if pocao.tem_efeito_adicional:
        if pocao.efeito_automatizado:
            # Única categoria automatizada hoje: PV temporário, reaproveita
            # Personagem.pv_temporario (que já existe desde o combate).
            p.pv_temporario = max(p.pv_temporario, pocao.efeito_valor)
            p.save(update_fields=["pv_temporario"])
            avisos.append(f'{pocao.nome}: +{pocao.efeito_valor} PV temporário.')
        else:
            avisos.append(
                f'{pocao.nome}: efeito adicional não automatizado — '
                f'{pocao.efeito_rotulo}. Aplique manualmente.'
            )

    pocao.quantidade -= 1
    if pocao.quantidade <= 0:
        pocao.delete()
    else:
        pocao.save(update_fields=["quantidade"])

    return avisos
