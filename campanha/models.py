import math

from django.db import models

from . import constants


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

    # Combate / corpo
    ca = models.PositiveSmallIntegerField("Classe de Armadura", default=10)
    pv_maximo = models.PositiveSmallIntegerField("PV Máximo", default=1)
    pv_atual = models.IntegerField("PV Atual", default=1)  # pode chegar a 0/negativo
    pv_temporario = models.PositiveSmallIntegerField("PV Temporário", default=0)
    deslocamento = models.PositiveSmallIntegerField("Deslocamento (m)", default=9)

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
        return self.mod_destreza


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


class ItemInventario(models.Model):
    """Item do inventário do personagem."""

    TIPOS = [
        ("equipado", "Equipado"),
        ("mochila", "Mochila"),
        ("magico", "Item Mágico"),
    ]

    personagem = models.ForeignKey(
        Personagem, related_name="itens", on_delete=models.CASCADE
    )
    nome = models.CharField("Nome", max_length=150)
    tipo = models.CharField("Tipo", max_length=10, choices=TIPOS, default="mochila")
    quantidade = models.PositiveIntegerField("Quantidade", default=1)
    atributos_efeito = models.TextField("Atributos / Efeito", blank=True)
    lore = models.TextField("Lore / História", blank=True)

    class Meta:
        verbose_name = "Item de Inventário"
        verbose_name_plural = "Itens de Inventário"
        ordering = ["tipo", "nome"]

    def __str__(self):
        return self.nome


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

    titulo = models.CharField("Título", max_length=200)
    descricao = models.TextField("Descrição / Objetivos", blank=True)
    status = models.CharField("Status", max_length=10, choices=STATUS, default="ativa")
    resultado = models.TextField("Resultado", blank=True)

    class Meta:
        verbose_name = "Missão"
        verbose_name_plural = "Missões"
        ordering = ["status", "titulo"]

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
