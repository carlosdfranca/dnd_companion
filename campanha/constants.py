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
