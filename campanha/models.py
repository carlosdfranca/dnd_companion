import math

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe

from . import constants, regras


def calcular_modificador(valor):
    """Modificador de atributo em D&D 5e: floor((valor - 10) / 2)."""
    return math.floor((valor - 10) / 2)


class Personagem(models.Model):
    """Ficha do personagem. Hoje há um só; FKs mantidas para multi-personagem futuro."""

    nome = models.CharField("Nome", max_length=120)
    raca = models.CharField("Raça", max_length=80, blank=True)
    classe = models.CharField("Classe", max_length=120, blank=True)
    nivel = models.PositiveSmallIntegerField("Nível", default=1)

    # Atributos (apenas o valor é armazenado; o modificador é calculado)
    forca = models.PositiveSmallIntegerField("Força", default=10)
    destreza = models.PositiveSmallIntegerField("Destreza", default=10)
    constituicao = models.PositiveSmallIntegerField("Constituição", default=10)
    inteligencia = models.PositiveSmallIntegerField("Inteligência", default=10)
    sabedoria = models.PositiveSmallIntegerField("Sabedoria", default=10)
    carisma = models.PositiveSmallIntegerField("Carisma", default=10)

    bonus_proficiencia = models.PositiveSmallIntegerField("Bônus de Proficiência", default=2)
    iniciativa_bonus   = models.SmallIntegerField("Bônus extra de Iniciativa", default=0,
                             help_text="Adicione aqui qualquer bônus extra (ex.: Bônus de Proficiência se tiver o feat/recurso correspondente).")

    # Combate / corpo
    ca_override = models.PositiveSmallIntegerField(
        "CA (override manual)", null=True, blank=True,
        help_text="Deixe em branco para calcular automaticamente a partir do "
                  "equipamento. Preencha só quando o motor não conseguir modelar algo.",
    )
    estilo_ca = models.CharField(
        "Estilo de CA sem armadura", max_length=12,
        choices=constants.ESTILO_CA_CHOICES, default="desarmado",
        help_text="Usado como base da CA quando nenhuma armadura corporal estiver equipada.",
    )
    pv_maximo = models.PositiveSmallIntegerField("PV Máximo", default=1)
    pv_atual = models.IntegerField("PV Atual", default=1)  # pode chegar a 0/negativo
    pv_temporario = models.PositiveSmallIntegerField("PV Temporário", default=0)
    deslocamento = models.PositiveSmallIntegerField("Deslocamento (m)", default=9)
    furia_ativa = models.BooleanField("Fúria ativa", default=False)
    bonus_dano_furia = models.PositiveSmallIntegerField(
        "Bônus de dano da Fúria", default=2,
        help_text="Somado ao dano dos ataques enquanto a Fúria estiver ativa. Cresce com o nível de bárbaro.",
    )

    background = models.TextField("Background / História", blank=True)

    # Moedas (campos diretos, 1:1 com o personagem)
    moedas_pc = models.PositiveIntegerField("Peças de Cobre", default=0)
    moedas_pp = models.PositiveIntegerField("Peças de Prata", default=0)
    moedas_pe = models.PositiveIntegerField("Peças de Electro", default=0)
    moedas_po = models.PositiveIntegerField("Peças de Ouro", default=0)
    moedas_pl = models.PositiveIntegerField("Peças de Platina", default=0)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Personagem"
        verbose_name_plural = "Personagens"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    # --- Modificadores ---
    def modificador(self, atributo):
        """Modificador de um atributo pelo nome do campo (ex.: 'forca')."""
        return calcular_modificador(getattr(self, atributo))

    @property
    def mod_forca(self):
        return calcular_modificador(self.forca)

    @property
    def mod_destreza(self):
        return calcular_modificador(self.destreza)

    @property
    def mod_constituicao(self):
        return calcular_modificador(self.constituicao)

    @property
    def mod_inteligencia(self):
        return calcular_modificador(self.inteligencia)

    @property
    def mod_sabedoria(self):
        return calcular_modificador(self.sabedoria)

    @property
    def mod_carisma(self):
        return calcular_modificador(self.carisma)

    @property
    def iniciativa(self):
        return (
            self.mod_destreza + self.iniciativa_bonus
            + regras.bonus_para(self.efeitos_ativos, "iniciativa")
        )

    # --- Efeitos de equipamento (ver campanha/regras.py) ---
    @cached_property
    def efeitos_ativos(self):
        """Bundle memoizado (2 queries) dos equipamentos ativos + seus EfeitoItem.

        cached_property vive só na instância Python em memória — não sobrevive
        entre requests, então não precisa de invalidação explícita: cada view
        que carrega o Personagem começa com um cache limpo.
        """
        return regras.coletar_efeitos(self)

    @property
    def ca_calculada(self):
        return regras.ca_calculada(self)

    @property
    def ca(self):
        """CA efetiva: o override manual se preenchido, senão a calculada."""
        return self.ca_override if self.ca_override is not None else self.ca_calculada

    @property
    def ca_detalhe(self):
        """[(rótulo, valor)] com a composição da CA, para exibir um tooltip."""
        return regras.detalhar_ca(self)

    # --- Carga e sintonização ---
    @property
    def carga_atual(self):
        return regras.carga_total(self)

    @property
    def capacidade_carga(self):
        return regras.capacidade_carga(self)

    @property
    def percentual_carga(self):
        capacidade = self.capacidade_carga
        if not capacidade:
            return 0
        return max(0, min(100, round(self.carga_atual * 100 / capacidade)))

    @property
    def sobrecarregado(self):
        return self.carga_atual > self.capacidade_carga

    @property
    def sintonizados_count(self):
        return self.itens.filter(sintonizado=True).count()

    @property
    def limite_sintonizacao(self):
        return constants.LIMITE_SINTONIZACAO

    @property
    def excedeu_sintonizacao(self):
        return self.sintonizados_count > self.limite_sintonizacao


class Pericia(models.Model):
    """Perícia do personagem. Só o booleano de proficiência é pessoal; o resto é regra fixa."""

    personagem = models.ForeignKey(
        Personagem, related_name="pericias", on_delete=models.CASCADE
    )
    identificador = models.CharField(max_length=40, choices=constants.PERICIA_CHOICES)
    proficiente = models.BooleanField("Proficiente", default=False)

    class Meta:
        verbose_name = "Perícia"
        verbose_name_plural = "Perícias"
        constraints = [
            models.UniqueConstraint(
                fields=["personagem", "identificador"], name="uniq_pericia_personagem"
            )
        ]

    def __str__(self):
        return f"{self.rotulo} ({self.personagem})"

    @property
    def rotulo(self):
        return constants.PERICIA_MAP.get(self.identificador, (self.identificador, ""))[0]

    @property
    def atributo(self):
        """Nome do campo de atributo regente (ex.: 'destreza')."""
        return constants.PERICIA_MAP.get(self.identificador, ("", "forca"))[1]

    @property
    def ordem(self):
        return constants.PERICIA_ORDEM.get(self.identificador, 999)

    @property
    def modificador_total(self):
        total = self.personagem.modificador(self.atributo)
        if self.proficiente:
            total += self.personagem.bonus_proficiencia
        total += regras.bonus_para(self.personagem.efeitos_ativos, "pericia")
        return total


class Salvaguarda(models.Model):
    """Salvaguarda (saving throw) do personagem."""

    personagem = models.ForeignKey(
        Personagem, related_name="salvaguardas", on_delete=models.CASCADE
    )
    identificador = models.CharField(max_length=20, choices=constants.SALVAGUARDA_CHOICES)
    proficiente = models.BooleanField("Proficiente", default=False)

    class Meta:
        verbose_name = "Salvaguarda"
        verbose_name_plural = "Salvaguardas"
        constraints = [
            models.UniqueConstraint(
                fields=["personagem", "identificador"], name="uniq_salvaguarda_personagem"
            )
        ]

    def __str__(self):
        return f"{self.rotulo} ({self.personagem})"

    @property
    def rotulo(self):
        return constants.SALVAGUARDA_MAP.get(self.identificador, (self.identificador, ""))[0]

    @property
    def atributo(self):
        return constants.SALVAGUARDA_MAP.get(self.identificador, ("", self.identificador))[1]

    @property
    def ordem(self):
        return constants.SALVAGUARDA_ORDEM.get(self.identificador, 999)

    @property
    def modificador_total(self):
        total = self.personagem.modificador(self.atributo)
        if self.proficiente:
            total += self.personagem.bonus_proficiencia
        total += regras.bonus_para(
            self.personagem.efeitos_ativos, "salvaguarda", self.identificador
        )
        return total


class RecursoDeCombate(models.Model):
    """Recurso de combate com usos limitados (ex.: Rage, Stone's Endurance)."""

    RECUPERACAO = [
        ("curto", "Descanso Curto"),
        ("longo", "Descanso Longo"),
        ("nenhum", "Nenhum"),
    ]

    personagem = models.ForeignKey(
        Personagem, related_name="recursos", on_delete=models.CASCADE
    )
    nome = models.CharField("Nome", max_length=120)
    descricao = models.TextField("Descrição / Efeito", blank=True)
    usos_totais = models.PositiveSmallIntegerField("Usos Totais", default=1)
    usos_restantes = models.PositiveSmallIntegerField("Usos Restantes", default=1)
    recuperacao = models.CharField(
        "Recuperação", max_length=10, choices=RECUPERACAO, default="longo"
    )
    checklist_turno = models.TextField("Checklist de Turno", blank=True)

    class Meta:
        verbose_name = "Recurso de Combate"
        verbose_name_plural = "Recursos de Combate"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


# Nota: o model Ataque foi removido. Ataques agora derivam das armas equipadas
# (ver campanha/regras.py, fase 2 do sistema de itens estruturado) — manter uma
# tabela de ataques cadastrados à mão criaria uma segunda fonte de verdade que
# pode divergir da arma equipada (dano, bônus, modo de empunhadura).


class ItemBase(models.Model):
    """Campos comuns a todo item de inventário (equipamento, poção, componente...).

    Base ABSTRATA — cada subsistema (equipamento, poções, alquimia, colheita)
    tem comportamento e formato de dado próprios demais para caber numa tabela
    só (uma query polimórfica sobre "todos os itens" nunca é o que a UI precisa
    — cada subsistema é uma seção com layout diferente). O que é genuinamente
    comum entre eles — dono, quantidade, raridade, peso, lore — fica aqui para
    não duplicar a declaração de campo em cada model concreto.
    """

    personagem = models.ForeignKey(Personagem, on_delete=models.CASCADE)
    nome = models.CharField("Nome", max_length=150)
    quantidade = models.PositiveIntegerField("Quantidade", default=1)
    raridade = models.CharField(
        "Raridade", max_length=12, choices=constants.RARIDADE_CHOICES, default="comum"
    )
    peso = models.DecimalField(
        "Peso (kg, por unidade)", max_digits=6, decimal_places=2, default=0,
        help_text="Usado para o total de carga (capacidade = Força × 7,5 kg).",
    )
    lore = models.TextField("Lore / História", blank=True)

    class Meta:
        abstract = True
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Equipamento(ItemBase):
    """Item de equipamento: arma, armadura, escudo ou acessório.

    `slot` indica onde está equipado ("" = na mochila). A ocupação de DOIS
    slots por uma arma de duas mãos é sempre DERIVADA de `slot` +
    `empunhadura`/`duas_maos` (ver `slots_ocupados`) — nunca armazenada como
    coluna própria, para não correr o risco de dessincronizar do estado real.

    `requer_sintonizacao` é uma propriedade do ITEM (a regra do item exige
    sintonia); `sintonizado` é o ESTADO do personagem em relação a ele — a
    distinção é o que torna o limite de `constants.LIMITE_SINTONIZACAO` itens
    sintonizados uma regra de verdade (ver `efeitos_habilitados`) e não só um
    contador visual.
    """

    # Redeclarado (em vez de herdado de ItemBase) só para manter o
    # related_name="itens" que views.py e os templates já usam — trocar para
    # "equipamentos" fica para quando essas telas forem atualizadas.
    personagem = models.ForeignKey(Personagem, related_name="itens", on_delete=models.CASCADE)

    # Vestigial: mantido só até uma migração futura remover a coluna. A
    # localização real de hoje em diante é decidida por `slot` (""=mochila).
    TIPOS = [
        ("equipado", "Equipado"),
        ("mochila", "Mochila"),
    ]
    tipo = models.CharField(
        "Localização (legado)", max_length=10, choices=TIPOS, default="mochila",
        help_text="Campo legado — a localização real é decidida pelo slot.",
    )

    categoria = models.CharField(
        "Categoria", max_length=12,
        choices=constants.CATEGORIA_EQUIPAMENTO_CHOICES, default="diverso",
    )
    # null=True (em vez de blank/default="") de propósito: é a forma nativa do
    # MySQL de conseguir "único, exceto quando vazio" — o InnoDB trata cada
    # NULL como distinto numa UNIQUE, então vários itens podem ter slot NULL
    # (mochila) mas só um pode ocupar cada slot real. SQLite suportaria um
    # UniqueConstraint com `condition`, mas o banco deste projeto é MySQL
    # (ver settings.py), que não suporta índice único condicional (W036).
    slot = models.CharField(
        "Slot equipado", max_length=20, choices=constants.SLOT_CHOICES,
        null=True, blank=True, default=None, help_text="Em branco = na mochila.",
    )
    slot_padrao = models.CharField(
        "Slot padrão ao equipar", max_length=20, choices=constants.SLOT_CHOICES,
        blank=True, default="",
    )
    empunhadura = models.CharField(
        "Empunhadura", max_length=4, choices=constants.EMPUNHADURA_CHOICES, default="uma",
    )
    duas_maos = models.BooleanField(
        "Sempre duas mãos", default=False,
        help_text="Arma inerentemente de duas mãos (não versátil).",
    )
    versatil = models.BooleanField(
        "Versátil", default=False,
        help_text="Muda o dado de dano quando empunhada com duas mãos.",
    )

    magico = models.BooleanField("Item Mágico", default=False)
    requer_sintonizacao = models.BooleanField(
        "Requer Sintonização", default=False,
        help_text="Propriedade do item — junto com 'Sintonizado' decide se os efeitos contam.",
    )
    sintonizado = models.BooleanField(
        "Sintonizado", default=False,
        help_text="Estado do personagem. Só é relevante se 'Requer Sintonização' for verdadeiro.",
    )

    # Dados de arma. dano_qtd_dados == 0 significa "este item não é uma arma".
    dano_qtd_dados = models.PositiveSmallIntegerField("Qtd. de Dados de Dano", default=0)
    dano_faces = models.PositiveSmallIntegerField(
        "Dado de Dano", choices=constants.FACES_DADO, default=8
    )
    dano_faces_versatil = models.PositiveSmallIntegerField(
        "Dado de Dano (versátil, 2 mãos)", choices=constants.FACES_DADO,
        null=True, blank=True,
    )
    tipo_dano = models.CharField(
        "Tipo de Dano", max_length=15, choices=constants.TIPO_DANO_CHOICES, blank=True,
    )
    atributo_ataque = models.CharField(
        "Atributo de Ataque", max_length=12, choices=constants.ATRIBUTO_CHOICES,
        default="forca",
    )
    proficiente = models.BooleanField("Proficiente", default=True)
    alcance = models.CharField("Alcance", max_length=40, blank=True)

    # Dados de armadura VESTIDA (não escudo). O cap de Destreza não é aditivo,
    # então não vira EfeitoItem — é resolvido em campanha.regras.ca_base.
    categoria_armadura = models.CharField(
        "Categoria de Armadura", max_length=10, blank=True,
        choices=constants.CATEGORIA_ARMADURA_CHOICES,
        help_text="Preencha só se este item for uma armadura VESTIDA (não escudo).",
    )
    ca_base_armadura = models.PositiveSmallIntegerField(
        "CA base da armadura", null=True, blank=True,
    )

    propriedades_texto = models.TextField(
        "Propriedades (texto livre)", blank=True,
        help_text="Regra narrativa que o motor não automatiza (ex.: Derrubar).",
    )
    atributos_efeito_legado = models.TextField(
        "Texto original (legado)", blank=True, editable=False,
        help_text="Preservado do antigo campo 'Atributos / Efeito' na migração para efeitos estruturados.",
    )
    ordem = models.PositiveSmallIntegerField("Ordem", default=0)

    class Meta:
        verbose_name = "Equipamento"
        verbose_name_plural = "Equipamentos"
        ordering = ["slot", "ordem", "nome"]
        constraints = [
            # Sem `condition`: no MySQL, múltiplas linhas com slot=NULL
            # (mochila) já são permitidas por padrão numa UNIQUE comum —
            # só slots não-nulos precisam ser únicos por personagem.
            models.UniqueConstraint(
                fields=["personagem", "slot"],
                name="uniq_equipamento_slot_personagem",
            )
        ]

    @property
    def slots_ocupados(self):
        """Slots fisicamente ocupados por este item — derivado, nunca armazenado."""
        if not self.slot:
            return []
        if self.slot == "mao_principal" and (self.duas_maos or self.empunhadura == "duas"):
            return ["mao_principal", "mao_secundaria"]
        return [self.slot]

    @property
    def efeitos_habilitados(self):
        """Os EfeitoItem deste equipamento contam no cálculo? Ver docstring da classe."""
        return bool(self.slot) and (not self.requer_sintonizacao or self.sintonizado)

    @property
    def dado_dano(self):
        """'NdM' de dano, respeitando o dado versátil quando empunhado com 2 mãos."""
        faces = (
            self.dano_faces_versatil
            if (self.versatil and self.empunhadura == "duas" and self.dano_faces_versatil)
            else self.dano_faces
        )
        return f"{self.dano_qtd_dados}d{faces}"

    @property
    def icone_categoria(self):
        """Caminho de template do ícone SVG da categoria (para o slot
        ocupado exibir um glifo em vez de só o nome). Ver constants.CATEGORIA_ICONES."""
        return constants.CATEGORIA_ICONES.get(self.categoria, "")


class EfeitoItem(models.Model):
    """Um efeito estruturado de um Equipamento. Uma linha = um efeito.

    `categoria` é o discriminador: os campos irrelevantes para a categoria
    escolhida ficam em branco e são ignorados pelo motor (campanha/regras.py).
    Linhas 'informativo' NUNCA são lidas pelo motor de cálculo — são a marca
    explícita de "isto não é automatizado" (ex.: crítico vira acerto normal
    do Adamantine Armor), sem precisar de um booleano `automatico` à parte.
    """

    equipamento = models.ForeignKey(
        Equipamento, related_name="efeitos", on_delete=models.CASCADE
    )
    categoria = models.CharField(
        "Categoria", max_length=15,
        choices=constants.CATEGORIA_EFEITO_CHOICES, default="numerico",
    )

    # --- numérico ---
    alvo = models.CharField(
        "Alvo", max_length=30, blank=True, choices=constants.ALVO_EFEITO_CHOICES,
    )
    valor = models.SmallIntegerField("Valor", default=0)
    tipo_bonus = models.CharField(
        "Tipo de Bônus", max_length=20, blank=True, choices=constants.TIPO_BONUS_CHOICES,
        help_text="Bônus do MESMO tipo não acumulam (vale o maior). "
                  "Deixe em branco para um bônus sem tipo, que sempre acumula.",
    )

    # --- palavra-chave ---
    palavra_chave = models.CharField(
        "Palavra-chave", max_length=25, blank=True, choices=constants.PALAVRA_CHAVE_CHOICES,
    )
    tipo_dano = models.CharField(
        "Tipo de Dano", max_length=15, blank=True, choices=constants.TIPO_DANO_CHOICES,
    )

    # --- comum a todas ---
    condicao = models.CharField(
        "Condição", max_length=120, blank=True,
        help_text="Se preenchido, o efeito é SITUACIONAL: aparece na ficha, mas NÃO "
                  "é somado automaticamente. Ex.: 'apenas contra mortos-vivos'.",
    )
    descricao = models.CharField("Descrição", max_length=250, blank=True)
    ordem = models.PositiveSmallIntegerField("Ordem", default=0)

    class Meta:
        verbose_name = "Efeito de Item"
        verbose_name_plural = "Efeitos de Item"
        ordering = ["ordem", "id"]

    def __str__(self):
        return self.rotulo

    def clean(self):
        erros = {}
        if self.categoria == "numerico":
            if not self.alvo:
                erros["alvo"] = "Obrigatório para efeito numérico."
            self.palavra_chave = self.tipo_dano = ""
        elif self.categoria == "palavra_chave":
            if not self.palavra_chave:
                erros["palavra_chave"] = "Obrigatório."
            else:
                qualif = constants.PALAVRA_CHAVE_MAP.get(self.palavra_chave, ("", "nenhum"))[1]
                if qualif == "tipo_dano" and not self.tipo_dano:
                    erros["tipo_dano"] = "Escolha o tipo de dano."
                if qualif == "alvo" and not self.alvo:
                    erros["alvo"] = "Escolha o alvo (ex.: Salvaguarda de Destreza)."
                if qualif == "nenhum" and not self.descricao:
                    erros["descricao"] = "Descreva o efeito."
            self.valor, self.tipo_bonus = 0, ""
        else:  # informativo
            if not self.descricao:
                erros["descricao"] = "Descreva a regra."
            self.alvo = self.tipo_bonus = self.palavra_chave = self.tipo_dano = ""
            self.valor = 0
        if erros:
            raise ValidationError(erros)

    @property
    def rotulo(self):
        """Texto humano do efeito: a descrição manual, ou gerado das constantes."""
        if self.descricao:
            return self.descricao
        if self.categoria == "numerico":
            alvo = constants.ALVO_EFEITO_MAP.get(self.alvo, (self.alvo, "", ""))[0]
            sinal = "+" if self.valor >= 0 else "−"
            tipo = constants.TIPO_BONUS_MAP.get(self.tipo_bonus, ("",))[0]
            return f"{sinal}{abs(self.valor)} em {alvo}" + (f" ({tipo})" if tipo else "")
        if self.categoria == "palavra_chave":
            pc = constants.PALAVRA_CHAVE_MAP.get(self.palavra_chave, (self.palavra_chave, ""))[0]
            qual = (
                constants.TIPO_DANO_MAP.get(self.tipo_dano, ("",))[0]
                or constants.ALVO_EFEITO_MAP.get(self.alvo, ("",))[0]
            )
            return f"{pc}: {qual}" if qual else pc
        return self.get_categoria_display()


class Pocao(ItemBase):
    """Poção consumível.

    Cura = `cura_qtd_dados` × `cura_faces` + `cura_bonus` — três inteiros,
    sem parser de expressão de dado. Cobrem qualquer poção de cura impressa
    e não aceitam entrada malformada (mesmo raciocínio do antigo model
    Ataque, removido na Fase 1).

    O efeito adicional é 4 campos planos, e não reaproveita `EfeitoItem`:
    o efeito de uma poção é PONTUAL, aplicado uma vez no momento de uso
    (`campanha.regras.aplicar_pocao`); `EfeitoItem` é o vocabulário de
    modificadores CONTÍNUOS agregados enquanto um equipamento está
    equipado. Ciclos de vida diferentes → armazenamento diferente.
    """

    personagem = models.ForeignKey(Personagem, related_name="pocoes", on_delete=models.CASCADE)

    cura_qtd_dados = models.PositiveSmallIntegerField("Qtd. de Dados de Cura", default=1)
    cura_faces = models.PositiveSmallIntegerField(
        "Dado de Cura", choices=constants.FACES_DADO, default=4
    )
    cura_bonus = models.SmallIntegerField("Bônus de Cura", default=0)

    efeito_categoria = models.CharField(
        "Categoria do Efeito Adicional", max_length=20, blank=True,
        choices=constants.EFEITO_POCAO_CHOICES,
        help_text="Só 'PV Temporário' é aplicado automaticamente hoje; as "
                  "demais categorias aparecem como aviso para aplicar na mão.",
    )
    efeito_alvo = models.CharField(
        "Alvo do Efeito Adicional", max_length=60, blank=True,
        help_text="Livre — o que significa depende da categoria (ex.: tipo de dano, condição, atributo).",
    )
    efeito_valor = models.SmallIntegerField("Valor do Efeito Adicional", default=0)
    efeito_descricao = models.CharField("Descrição do Efeito Adicional", max_length=250, blank=True)

    class Meta:
        verbose_name = "Poção"
        verbose_name_plural = "Poções"
        ordering = ["nome"]

    @property
    def formula_cura(self):
        formula = f"{self.cura_qtd_dados}d{self.cura_faces}"
        if self.cura_bonus:
            formula += f" +{self.cura_bonus}" if self.cura_bonus > 0 else f" −{abs(self.cura_bonus)}"
        return formula

    @property
    def tem_efeito_adicional(self):
        return bool(self.efeito_categoria) and self.efeito_categoria != "nenhum"

    @property
    def efeito_automatizado(self):
        return self.efeito_categoria in constants.EFEITOS_POCAO_AUTOMATIZADOS

    @property
    def efeito_rotulo(self):
        """Texto humano do efeito adicional, para exibir na lista de poções."""
        if not self.tem_efeito_adicional:
            return ""
        label = constants.EFEITO_POCAO_MAP.get(self.efeito_categoria, self.efeito_categoria)
        if self.efeito_descricao:
            return f"{label}: {self.efeito_descricao}"
        if self.efeito_alvo:
            return f"{label} ({self.efeito_alvo}, {self.efeito_valor:+d})"
        return label


class ComponenteAlquimico(ItemBase):
    """Componente alquímico (planta). Armazenamento puro — sem slot, sem
    efeito mecânico, sem motor de regras (ao contrário de Equipamento)."""

    personagem = models.ForeignKey(
        Personagem, related_name="componentes_alquimicos", on_delete=models.CASCADE
    )
    reagente = models.CharField(
        "Reagente", max_length=12, choices=constants.REAGENTE_CHOICES,
    )

    class Meta:
        verbose_name = "Componente Alquímico"
        verbose_name_plural = "Componentes Alquímicos"
        ordering = ["nome"]


class BaseAlquimica(ItemBase):
    """Base alquímica — igual a ComponenteAlquimico, mas sem reagente."""

    personagem = models.ForeignKey(
        Personagem, related_name="bases_alquimicas", on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = "Base Alquímica"
        verbose_name_plural = "Bases Alquímicas"
        ordering = ["nome"]


class Essencia(models.Model):
    """Contador agregado de essência por tier — não tem nome individual.

    Segue exatamente o padrão de Pericia/Salvaguarda (não herda ItemBase:
    não tem nome, peso ou raridade próprios): uma linha fixa por
    personagem×tier, semeada por signal (`signals.seed_caracteristicas`) e
    editada como formset (`quantidade` é o único campo pessoal). Por não
    herdar ItemBase, não tem `peso` — não conta em `regras.carga_total`,
    intencionalmente: é um contador mágico abstrato, sem forma física.
    """

    personagem = models.ForeignKey(
        Personagem, related_name="essencias", on_delete=models.CASCADE
    )
    tier = models.CharField(max_length=10, choices=constants.ESSENCIA_CHOICES)
    quantidade = models.PositiveIntegerField("Quantidade", default=0)

    class Meta:
        verbose_name = "Essência"
        verbose_name_plural = "Essências"
        constraints = [
            models.UniqueConstraint(
                fields=["personagem", "tier"], name="uniq_essencia_personagem"
            )
        ]

    def __str__(self):
        return f"{self.rotulo} ({self.personagem})"

    @property
    def rotulo(self):
        return dict(constants.ESSENCIA_CHOICES).get(self.tier, self.tier)

    @property
    def ordem(self):
        return constants.ESSENCIA_ORDEM.get(self.tier, 999)


class ComponenteCriatura(ItemBase):
    """Componente de criatura obtido por colheita. Armazenamento puro,
    mesmo raciocínio de ComponenteAlquimico/BaseAlquimica."""

    personagem = models.ForeignKey(
        Personagem, related_name="componentes_criatura", on_delete=models.CASCADE
    )
    tipo_origem = models.CharField(
        "Tipo de Origem", max_length=15, choices=constants.TIPO_CRIATURA_CHOICES,
    )

    class Meta:
        verbose_name = "Componente de Criatura"
        verbose_name_plural = "Componentes de Criatura"
        ordering = ["nome"]


class Local(models.Model):
    """Local do mundo (cidade, vila, região, base...). Compartilhado pela campanha."""

    TIPOS = [
        ("cidade", "Cidade"),
        ("vila", "Vila"),
        ("regiao", "Região"),
        ("base", "Base"),
        ("outro", "Outro"),
    ]

    nome = models.CharField("Nome", max_length=150)
    tipo = models.CharField("Tipo", max_length=10, choices=TIPOS, blank=True)
    descricao = models.TextField("Descrição / Notas", blank=True)
    status = models.CharField("Status Atual", max_length=150, blank=True)
    imagem = models.ImageField("Ilustração", upload_to="locais/", blank=True, null=True)
    mapa = models.ImageField(
        "Mapa", upload_to="locais/mapas/", blank=True, null=True,
        help_text="Mapa do local, se houver.",
    )

    class Meta:
        verbose_name = "Local"
        verbose_name_plural = "Locais"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class NPC(models.Model):
    """Personagem não-jogável. Compartilhado pela campanha."""

    RELACOES = [
        ("aliado", "Aliado"),
        ("suspeito", "Suspeito"),
        ("inimigo", "Inimigo"),
        ("neutro", "Neutro"),
        ("desconhecido", "Desconhecido"),
    ]

    nome = models.CharField("Nome", max_length=150)
    local = models.ForeignKey(
        Local, null=True, blank=True, related_name="npcs", on_delete=models.SET_NULL
    )
    descricao = models.TextField("Descrição / Papel", blank=True)
    relacao_grupo = models.CharField(
        "Relação com o Grupo", max_length=15, choices=RELACOES, default="neutro"
    )
    imagem = models.ImageField("Imagem", upload_to="npcs/", blank=True, null=True)

    class Meta:
        verbose_name = "NPC"
        verbose_name_plural = "NPCs"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Missao(models.Model):
    """Missão / quest. Compartilhada pela campanha."""

    STATUS = [
        ("ativa", "Ativa"),
        ("concluida", "Concluída"),
    ]

    TIPOS = [
        ("principal", "Missão Principal"),
        ("contrato", "Contrato"),
        ("secundaria", "Missão Secundária"),
    ]

    titulo    = models.CharField("Título", max_length=200)
    descricao = models.TextField("Descrição / Objetivos", blank=True)
    tipo      = models.CharField("Tipo", max_length=12, choices=TIPOS, default="secundaria")
    status    = models.CharField("Status", max_length=10, choices=STATUS, default="ativa")
    resultado = models.TextField("Resultado", blank=True)
    ordem     = models.PositiveSmallIntegerField("Ordem", default=0,
                    help_text="Posição no kanban; menor aparece primeiro. Ajustado ao arrastar.")

    class Meta:
        verbose_name = "Missão"
        verbose_name_plural = "Missões"
        ordering = ["tipo", "ordem", "titulo"]

    def __str__(self):
        return self.titulo


class ResumoSessao(models.Model):
    """Resumo de uma sessão de jogo."""

    numero = models.PositiveIntegerField("Número da Sessão")
    titulo = models.CharField("Título", max_length=200, blank=True)
    data = models.DateField("Data", null=True, blank=True)
    resumo = models.TextField("Resumo", blank=True)

    class Meta:
        verbose_name = "Resumo de Sessão"
        verbose_name_plural = "Resumos de Sessão"
        ordering = ["-numero"]

    def __str__(self):
        return f"Sessão {self.numero}" + (f" — {self.titulo}" if self.titulo else "")


class NotaCombate(models.Model):
    """Referência de habilidade/mecânica consultada durante o combate."""

    personagem = models.ForeignKey(
        Personagem, on_delete=models.CASCADE, related_name="notas_combate"
    )
    titulo   = models.CharField("Título", max_length=200)
    conteudo = models.TextField("Conteúdo", blank=True,
                   help_text="Descreva a mecânica, dano, condições, etc. Formatação livre.")
    ordem    = models.PositiveSmallIntegerField("Ordem", default=0,
                   help_text="Número menor aparece primeiro.")

    class Meta:
        verbose_name = "Nota de Combate"
        verbose_name_plural = "Notas de Combate"
        ordering = ["ordem", "titulo"]

    def __str__(self):
        return self.titulo

    @property
    def conteudo_html(self):
        from .markup import render_md
        return mark_safe(render_md(self.conteudo))


class InformacaoImportante(models.Model):
    """Anotação curta, opcionalmente ligada a uma missão ou NPC."""

    texto = models.CharField("Informação", max_length=300)
    missao = models.ForeignKey(
        Missao, null=True, blank=True, related_name="infos", on_delete=models.SET_NULL
    )
    npc = models.ForeignKey(
        NPC, null=True, blank=True, related_name="infos", on_delete=models.SET_NULL
    )

    class Meta:
        verbose_name = "Informação Importante"
        verbose_name_plural = "Informações Importantes"

    def __str__(self):
        return self.texto
