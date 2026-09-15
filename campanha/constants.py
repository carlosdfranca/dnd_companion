"""
Tabelas FIXAS de regras de D&D 5e (não vão para o banco como dados editáveis).

Cada linha de Pericia/Salvaguarda no banco guarda só o que é pessoal do personagem
(o booleano `proficiente` + a FK). O rótulo de exibição e o atributo regente vivem
aqui no código, indexados por um `identificador` estável.
"""

# Atributos canônicos (nome do campo no model Personagem -> rótulo de exibição)
ATRIBUTOS = [
    ("forca", "Força", "FOR"),
    ("destreza", "Destreza", "DES"),
    ("constituicao", "Constituição", "CON"),
    ("inteligencia", "Inteligência", "INT"),
    ("sabedoria", "Sabedoria", "SAB"),
    ("carisma", "Carisma", "CAR"),
]

# Choices derivado de ATRIBUTOS, para campos que escolhem "qual atributo" (ex.:
# atributo de ataque de uma arma).
ATRIBUTO_CHOICES = [(campo, label) for campo, label, _ in ATRIBUTOS]

# Perícias 5e: (identificador, rótulo, atributo regente)
PERICIAS = [
    ("acrobacia",       "Acrobacia",         "destreza"),
    ("adestrar_animais", "Adestrar Animais", "sabedoria"),
    ("arcanismo",       "Arcanismo",         "inteligencia"),
    ("atletismo",       "Atletismo",         "forca"),
    ("atuacao",         "Atuação",           "carisma"),
    ("enganacao",       "Enganação",         "carisma"),
    ("furtividade",     "Furtividade",       "destreza"),
    ("historia",        "História",          "inteligencia"),
    ("intimidacao",     "Intimidação",       "carisma"),
    ("intuicao",        "Intuição",          "sabedoria"),
    ("investigacao",    "Investigação",      "inteligencia"),
    ("medicina",        "Medicina",          "sabedoria"),
    ("natureza",        "Natureza",          "inteligencia"),
    ("percepcao",       "Percepção",         "sabedoria"),
    ("persuasao",       "Persuasão",         "carisma"),
    ("prestidigitacao", "Prestidigitação",   "destreza"),
    ("religiao",        "Religião",          "inteligencia"),
    ("sobrevivencia",   "Sobrevivência",     "sabedoria"),
]  # 18 perícias

# Salvaguardas 5e: (identificador, rótulo, atributo regente) — 1:1 com os atributos
SALVAGUARDAS = [
    ("forca",        "Força",        "forca"),
    ("destreza",     "Destreza",     "destreza"),
    ("constituicao", "Constituição", "constituicao"),
    ("inteligencia", "Inteligência", "inteligencia"),
    ("sabedoria",    "Sabedoria",    "sabedoria"),
    ("carisma",      "Carisma",      "carisma"),
]  # 6 salvaguardas

# Choices derivados (para os campos `identificador`)
PERICIA_CHOICES = [(ident, label) for ident, label, _ in PERICIAS]
SALVAGUARDA_CHOICES = [(ident, label) for ident, label, _ in SALVAGUARDAS]

# Mapas identificador -> (label, atributo regente) para lookups rápidos nos models/templates
PERICIA_MAP = {ident: (label, attr) for ident, label, attr in PERICIAS}
SALVAGUARDA_MAP = {ident: (label, attr) for ident, label, attr in SALVAGUARDAS}

# Ordem de exibição (índice por identificador) para manter a ficha sempre na mesma ordem
PERICIA_ORDEM = {ident: i for i, (ident, *_ ) in enumerate(PERICIAS)}
SALVAGUARDA_ORDEM = {ident: i for i, (ident, *_ ) in enumerate(SALVAGUARDAS)}


# ─────────────────────────────────────────────────────────────────────────────
# Efeitos estruturados de item (Equipamento / EfeitoItem) — ver campanha/regras.py
# ─────────────────────────────────────────────────────────────────────────────

# Categoria do efeito: (identificador, rótulo, ajuda)
# 'informativo' é a marca explícita de "o sistema NÃO automatiza isto" — o
# motor de regras nunca lê linhas dessa categoria, só exibe.
CATEGORIAS_EFEITO = [
    ("numerico",      "Bônus numérico", "Soma um valor a um alvo (CA, salvaguarda, ataque, dano)."),
    ("palavra_chave", "Palavra-chave",  "Resistência, imunidade, vantagem — não é um número."),
    ("informativo",   "Informativo",    "Regra que o sistema não automatiza; apenas exibe."),
]

# Alvo de um efeito numérico ou de vantagem/desvantagem: (identificador, rótulo, escopo, chave)
#   escopo -> qual cálculo consome o efeito ('ca', 'salvaguarda', 'ataque', ...)
#   chave  -> sub-alvo dentro do escopo; "" casa com TODOS os alvos do escopo.
#   As chaves de salvaguarda batem 1:1 com os identificadores de SALVAGUARDAS.
ALVOS_EFEITO = [
    ("ca",                 "Classe de Armadura",          "ca",          ""),
    ("salvaguardas_todas", "Todas as Salvaguardas",       "salvaguarda", ""),
    ("save_forca",         "Salvaguarda de Força",        "salvaguarda", "forca"),
    ("save_destreza",      "Salvaguarda de Destreza",     "salvaguarda", "destreza"),
    ("save_constituicao",  "Salvaguarda de Constituição", "salvaguarda", "constituicao"),
    ("save_inteligencia",  "Salvaguarda de Inteligência", "salvaguarda", "inteligencia"),
    ("save_sabedoria",     "Salvaguarda de Sabedoria",    "salvaguarda", "sabedoria"),
    ("save_carisma",       "Salvaguarda de Carisma",      "salvaguarda", "carisma"),
    ("ataque",             "Jogadas de Ataque",           "ataque",      ""),
    ("dano",               "Jogadas de Dano",             "dano",        ""),
    ("iniciativa",         "Iniciativa",                  "iniciativa",  ""),
    ("pericias_todas",     "Todos os testes de perícia",  "pericia",     ""),
]

# Tipos de bônus nomeados: (identificador, rótulo, ajuda)
# REGRA DE EMPILHAMENTO (5e): bônus do MESMO tipo não acumulam — vale o maior.
# Tipos diferentes acumulam entre si. Bônus SEM tipo ("") sempre acumulam.
TIPOS_BONUS = [
    ("armadura",      "Armadura",         "Bônus da armadura vestida."),
    ("escudo",        "Escudo",           "Bônus de escudo empunhado."),
    ("deflexao",      "Deflexão",         "Ex.: Manto de Proteção, Anel de Proteção."),
    ("natural",       "Armadura Natural", "Ex.: Amuleto de Armadura Natural."),
    ("aprimoramento", "Aprimoramento",    "Bônus mágico +1/+2/+3 de uma arma ou armadura."),
]

# Tipos de dano 5e: (identificador, rótulo)
TIPOS_DANO = [
    ("cortante",   "Cortante"),
    ("perfurante", "Perfurante"),
    ("concussao",  "Concussão"),
    ("acido",      "Ácido"),
    ("frio",       "Frio"),
    ("fogo",       "Fogo"),
    ("eletrico",   "Elétrico"),
    ("necrotico",  "Necrótico"),
    ("psiquico",   "Psíquico"),
    ("radiante",   "Radiante"),
    ("trovejante", "Trovejante"),
    ("veneno",     "Veneno"),
    ("energia",    "Energia (Força)"),
]  # 13 tipos de dano

# Palavras-chave de efeito: (identificador, rótulo, qualificador)
#   qualificador -> qual campo do EfeitoItem completa o sentido do efeito:
#   'tipo_dano' (resistência/imunidade/vulnerabilidade), 'alvo' (vantagem/
#   desvantagem em quê) ou 'nenhum' (só a descrição livre resolve).
PALAVRAS_CHAVE_EFEITO = [
    ("resistencia",       "Resistência a dano",     "tipo_dano"),
    ("imunidade",         "Imunidade a dano",       "tipo_dano"),
    ("vulnerabilidade",   "Vulnerabilidade a dano", "tipo_dano"),
    ("vantagem",          "Vantagem",               "alvo"),
    ("desvantagem",       "Desvantagem",            "alvo"),
    ("imunidade_condicao", "Imunidade a condição",  "nenhum"),
    ("visao_no_escuro",   "Visão no escuro",        "nenhum"),
]

# Estilo de CA base SEM armadura vestida (config por classe do personagem):
#   (identificador, rótulo, base, atributo_extra)
# CA = base + mod(Destreza) + mod(atributo_extra); atributo_extra "" = nenhum.
ESTILOS_CA = [
    ("desarmado", "Sem armadura (10 + DES)",              10, ""),
    ("barbaro",   "Defesa sem Armadura — Bárbaro (+CON)", 10, "constituicao"),
    ("monge",     "Defesa sem Armadura — Monge (+SAB)",   10, "sabedoria"),
    ("draconico", "Resiliência Dracônica (13 + DES)",     13, ""),
]

# Categorias de armadura vestida: (identificador, rótulo, limite_destreza)
# limite_destreza None = sem limite (armadura leve).
CATEGORIAS_ARMADURA = [
    ("leve",   "Armadura Leve",   None),
    ("media",  "Armadura Média",  2),
    ("pesada", "Armadura Pesada", 0),
]

# Slots de equipamento: (identificador, rótulo, ordem_grid)
SLOTS_EQUIPAMENTO = [
    ("mao_principal",   "Mão Principal",       0),
    ("mao_secundaria",  "Mão Secundária",      1),
    ("armadura_corporal", "Armadura Corporal", 2),
    ("capa",             "Capa / Manto",       3),
    ("cabeca",           "Cabeça",             4),
    ("colar",             "Colar / Amuleto",   5),
    ("cinto",             "Cinto",             6),
    ("anel_1",            "Anel 1",            7),
    ("anel_2",            "Anel 2",            8),
    ("luvas",             "Luvas",             9),
    ("botas",             "Botas",            10),
    ("municao",           "Munição",          11),
]  # 12 slots

# Categoria funcional do item de equipamento: (identificador, rótulo)
CATEGORIAS_EQUIPAMENTO = [
    ("arma",      "Arma"),
    ("armadura",  "Armadura"),
    ("escudo",    "Escudo"),
    ("acessorio", "Acessório"),
    ("municao",   "Munição"),
    ("diverso",   "Diverso"),
]

# Slot padrão ao equipar, usado só quando o item não tem `slot_padrao` próprio
# preenchido (ver campanha/regras.py:equipar).
SLOT_PADRAO_POR_CATEGORIA = {
    "arma": "mao_principal",
    "escudo": "mao_secundaria",
    "armadura": "armadura_corporal",
}

# Ícones do reskin da tela de Inventário — caminhos de TEMPLATE (não de
# static/), pra serem usados com `{% include %}` e ficarem coloríveis via
# CSS `color` (o `fill="currentColor"` já vem gravado no SVG). Ver
# campanha/templates/campanha/icons/CREDITS.txt para autoria/licença
# (game-icons.net, CC BY 3.0) — só os 12 SVGs realmente usados foram
# baixados, nada de pacote/CDN inteiro.
#
# SLOT_ICONES: ícone de fundo (esmaecido) mostrado no slot quando VAZIO.
SLOT_ICONES = {
    "mao_principal":      "campanha/icons/lorc__broadsword.svg",
    "mao_secundaria":     "campanha/icons/sbed__shield.svg",
    "armadura_corporal":  "campanha/icons/delapouite__chest-armor.svg",
    "capa":               "campanha/icons/delapouite__cape.svg",
    "cabeca":             "campanha/icons/sbed__helmet.svg",
    "colar":              "campanha/icons/lucasms__necklace.svg",
    "cinto":              "campanha/icons/lucasms__belt.svg",
    "anel_1":             "campanha/icons/delapouite__ring.svg",
    "anel_2":             "campanha/icons/delapouite__ring.svg",
    "luvas":              "campanha/icons/delapouite__gloves.svg",
    "botas":              "campanha/icons/lorc__boots.svg",
    "municao":            "campanha/icons/delapouite__quiver.svg",
}

# CATEGORIA_ICONES: ícone mostrado junto ao nome quando o slot está OCUPADO
# — por categoria do item (Equipamento.categoria), não por item individual
# (isso exigiria upload de imagem por item, fora de escopo).
CATEGORIA_ICONES = {
    "arma":      "campanha/icons/lorc__broadsword.svg",
    "armadura":  "campanha/icons/delapouite__chest-armor.svg",
    "escudo":    "campanha/icons/sbed__shield.svg",
    "acessorio": "campanha/icons/lucasms__necklace.svg",
    "municao":   "campanha/icons/delapouite__quiver.svg",
    "diverso":   "campanha/icons/delapouite__backpack.svg",
}

# Empunhadura de arma: (identificador, rótulo)
EMPUNHADURAS = [
    ("uma",  "Uma Mão"),
    ("duas", "Duas Mãos"),
]

# Dados de dano: (faces, rótulo) — mesma lista do antigo model Ataque
FACES_DADO = [
    (4, "d4"), (6, "d6"), (8, "d8"), (10, "d10"), (12, "d12"), (20, "d20"),
]

# Raridades 5e: (identificador, rótulo)
RARIDADES = [
    ("comum",     "Comum"),
    ("incomum",   "Incomum"),
    ("raro",      "Raro"),
    ("muito_raro", "Muito Raro"),
    ("lendario",  "Lendário"),
]

# Máximo de itens sintonizados simultaneamente (5e: 3).
LIMITE_SINTONIZACAO = 3

# ─────────────────────────────────────────────────────────────────────────────
# Poções (Fase 2) — ver campanha/regras.py:aplicar_pocao
# ─────────────────────────────────────────────────────────────────────────────

# Categoria do efeito adicional de uma poção: (identificador, rótulo)
# O efeito é PONTUAL (aplicado uma vez, no uso) — ciclo de vida diferente do
# EfeitoItem de equipamento, que é contínuo enquanto o item está equipado;
# por isso não reaproveita a tabela CATEGORIAS_EFEITO nem o model EfeitoItem.
# Só "pv_temporario" tem estado no Personagem para ser aplicado de verdade
# hoje (reaproveita `Personagem.pv_temporario`); as demais categorias são
# estruturadas mas exibidas como aviso para o jogador aplicar manualmente,
# no mesmo espírito do EfeitoItem categoria="informativo" da Fase 1 — o
# sistema não deve fingir automatizar o que não tem onde representar.
EFEITOS_POCAO = [
    ("nenhum",           "Nenhum"),
    ("pv_temporario",    "PV Temporário"),
    ("remove_condicao",  "Remove uma Condição"),
    ("resistencia_buff", "Resistência Temporária a um Tipo de Dano"),
    ("vantagem_buff",    "Vantagem Temporária em um Teste"),
    ("atributo_buff",    "Bônus Temporário a um Atributo"),
    ("outro",            "Outro (ver descrição)"),
]
EFEITO_POCAO_CHOICES = list(EFEITOS_POCAO)
EFEITO_POCAO_MAP = dict(EFEITOS_POCAO)

# Categorias que o motor aplica de verdade (mexem em algum campo do
# Personagem). Todo o resto em EFEITOS_POCAO vira aviso manual.
EFEITOS_POCAO_AUTOMATIZADOS = {"pv_temporario"}

# Capacidade de carga = FOR × este multiplicador, em kg (5e pt-br: FOR × 7,5 kg).
MULTIPLICADOR_CAPACIDADE_KG = 7.5

# ── Derivados ─────────────────────────────────────────────────────────────────
CATEGORIA_EFEITO_CHOICES   = [(i, l) for i, l, _ in CATEGORIAS_EFEITO]
ALVO_EFEITO_CHOICES        = [(i, l) for i, l, _, _ in ALVOS_EFEITO]
TIPO_BONUS_CHOICES         = [(i, l) for i, l, _ in TIPOS_BONUS]
TIPO_DANO_CHOICES          = list(TIPOS_DANO)
PALAVRA_CHAVE_CHOICES      = [(i, l) for i, l, _ in PALAVRAS_CHAVE_EFEITO]
ESTILO_CA_CHOICES          = [(i, l) for i, l, _, _ in ESTILOS_CA]
CATEGORIA_ARMADURA_CHOICES = [(i, l) for i, l, _ in CATEGORIAS_ARMADURA]
SLOT_CHOICES                = [(i, l) for i, l, _ in SLOTS_EQUIPAMENTO]
CATEGORIA_EQUIPAMENTO_CHOICES = list(CATEGORIAS_EQUIPAMENTO)
EMPUNHADURA_CHOICES         = list(EMPUNHADURAS)
RARIDADE_CHOICES            = list(RARIDADES)

CATEGORIA_EFEITO_MAP   = {i: (l, a) for i, l, a in CATEGORIAS_EFEITO}
ALVO_EFEITO_MAP        = {i: (l, e, c) for i, l, e, c in ALVOS_EFEITO}
TIPO_BONUS_MAP         = {i: (l, a) for i, l, a in TIPOS_BONUS}
TIPO_DANO_MAP          = {i: (l,) for i, l in TIPOS_DANO}
PALAVRA_CHAVE_MAP      = {i: (l, q) for i, l, q in PALAVRAS_CHAVE_EFEITO}
ESTILO_CA_MAP          = {i: (l, b, a) for i, l, b, a in ESTILOS_CA}
CATEGORIA_ARMADURA_MAP = {i: (l, lim) for i, l, lim in CATEGORIAS_ARMADURA}
SLOT_MAP                = {i: (l, o) for i, l, o in SLOTS_EQUIPAMENTO}

SLOT_ORDEM      = {i: o for i, _, o in SLOTS_EQUIPAMENTO}
TIPO_DANO_ORDEM = {i: n for n, (i, *_) in enumerate(TIPOS_DANO)}


# ─────────────────────────────────────────────────────────────────────────────
# Alquimia (Fase 2) — armazenamento puro, sem motor de regras, sem slot,
# sem efeito mecânico. Ver models.ComponenteAlquimico / models.BaseAlquimica.
# ─────────────────────────────────────────────────────────────────────────────

# Reagente de um componente alquímico (planta): (identificador, rótulo)
REAGENTES = [
    ("vento",    "Vento"),
    ("luz",      "Luz"),
    ("trevas",   "Trevas"),
    ("terra",    "Terra"),
    ("fogo",     "Fogo"),
    ("agua",     "Água"),
    ("natureza", "Natureza"),
    ("arcano",   "Arcano"),
]  # 8 reagentes
REAGENTE_CHOICES = list(REAGENTES)


# ─────────────────────────────────────────────────────────────────────────────
# Harvesting (Fase 2) — armazenamento puro. Ver models.Essencia /
# models.ComponenteCriatura.
# ─────────────────────────────────────────────────────────────────────────────

# Tier de Essência: (identificador, rótulo). Nomes mantidos em inglês — são
# terminologia própria do sistema de colheita/crafting da campanha, não um
# termo de regra 5e com tradução oficial (diferente de PERICIAS/SALVAGUARDAS,
# que traduzem porque são vocabulário do próprio 5e).
ESSENCIAS = [
    ("frail",  "Frail"),
    ("robust", "Robust"),
    ("potent", "Potent"),
    ("mythic", "Mythic"),
    ("deific", "Deific"),
]  # 5 tiers
ESSENCIA_CHOICES = list(ESSENCIAS)
ESSENCIA_ORDEM = {ident: i for i, (ident, _label) in enumerate(ESSENCIAS)}

# Tipo de origem de um componente de criatura: (identificador, rótulo).
# Mesmo raciocínio de ESSENCIAS — nomes mantidos em inglês.
TIPOS_CRIATURA = [
    ("beast",       "Beast"),
    ("monstrosity", "Monstrosity"),
    ("giant",       "Giant"),
    ("construct",   "Construct"),
    ("dragon",      "Dragon"),
    ("fiend",       "Fiend"),
    ("fey",         "Fey"),
    ("undead",      "Undead"),
    ("elemental",   "Elemental"),
    ("aberration",  "Aberration"),
    ("celestial",   "Celestial"),
    ("ooze",        "Ooze"),
    ("plant",       "Plant"),
    ("humanoid",    "Humanoid"),
]  # 14 tipos
TIPO_CRIATURA_CHOICES = list(TIPOS_CRIATURA)
