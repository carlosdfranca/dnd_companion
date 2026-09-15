# Migração de DADOS dos 8 registros reais de Equipamento (ex-ItemInventario)
# para o schema de efeitos estruturados criado em 0011.
#
# Escopo desta sessão é só Fase 1 (equipamento) — não existe ainda um model
# Pocao (fica para a fase 2), então "Poção de Cura Menor" permanece como
# Equipamento de mochila, só com peso preenchido; seu texto de cura continua
# em atributos_efeito_legado até a fase 2 estruturar poções de verdade.
#
# Ajuste do usuário sobre o Cloack of Protection: migrado como +1 CA e +1 em
# TODAS as salvaguardas (alvo="salvaguardas_todas"), não só Destreza — embora
# o texto original no banco dissesse só "salvaguardas de DEX", o usuário
# confirmou que a intenção real (ruling da mesa) é a regra oficial do 5e.
#
# `tipo` (legado) NÃO é tocado aqui — já reflete corretamente equipado/mochila
# desde antes desta migração e continua sendo o que as views atuais leem;
# `slot` é a informação nova que o motor de regras passa a consumir.

from decimal import Decimal

from django.db import migrations


# nome -> (campos do Equipamento, lista de kwargs de EfeitoItem)
MAPA_EQUIPAMENTO = {
    "Machado de Batalha": (
        {
            "categoria": "arma",
            "slot": "mao_principal",
            "slot_padrao": "mao_principal",
            "empunhadura": "uma",
            "versatil": True,
            "dano_qtd_dados": 1,
            "dano_faces": 8,
            "dano_faces_versatil": 10,
            "tipo_dano": "cortante",
            "atributo_ataque": "forca",
            "proficiente": True,
            "peso": Decimal("1.80"),
            "propriedades_texto": (
                "Propriedade Derrubar: se acertar, criatura faz save CON "
                "CD=8+prof+FOR ou cai Caído."
            ),
        },
        [],
    ),
    "Escudo": (
        {
            "categoria": "escudo",
            "slot": "mao_secundaria",
            "slot_padrao": "mao_secundaria",
            "peso": Decimal("2.70"),
        },
        [
            {"categoria": "numerico", "alvo": "ca", "valor": 2, "tipo_bonus": "escudo", "ordem": 0},
        ],
    ),
    "Ração": (
        {"peso": Decimal("0.30")},
        [],
    ),
    "Kit de Jogos (Dados)": (
        {
            "peso": Decimal("0.20"),
            "propriedades_texto": (
                "Proficiência em ferramentas. Útil para ganhar dinheiro, "
                "interações sociais, contatos, distrair NPCs."
            ),
        },
        [],
    ),
    "Corda": (
        {"peso": Decimal("4.50")},
        [],
    ),
    "Cantil": (
        {"peso": Decimal("1.00"), "lore": "Cheio"},
        [],
    ),
    "Cloack of Protection": (
        {
            "categoria": "acessorio",
            "slot": "capa",
            "slot_padrao": "capa",
            "sintonizado": True,
            "raridade": "incomum",
            "peso": Decimal("0.20"),
        },
        [
            {"categoria": "numerico", "alvo": "ca", "valor": 1, "tipo_bonus": "deflexao", "ordem": 0},
            {"categoria": "numerico", "alvo": "salvaguardas_todas", "valor": 1, "tipo_bonus": "", "ordem": 1},
        ],
    ),
    "Poção de Cura Menor": (
        {"peso": Decimal("0.25")},
        [],
    ),
}

# Estado "antes" de cada campo tocado acima — usado só pelo reverse, para não
# ter que adivinhar o default de cada campo na hora de desfazer.
CAMPOS_RESET = {
    "categoria": "diverso",
    "slot": "",
    "slot_padrao": "",
    "empunhadura": "uma",
    "duas_maos": False,
    "versatil": False,
    "sintonizado": False,
    "dano_qtd_dados": 0,
    "dano_faces": 8,
    "dano_faces_versatil": None,
    "tipo_dano": "",
    "atributo_ataque": "forca",
    "proficiente": True,
    "alcance": "",
    "categoria_armadura": "",
    "ca_base_armadura": None,
    "propriedades_texto": "",
    "raridade": "comum",
    "peso": Decimal("0"),
    "lore": "",
}


def migrar_dados(apps, schema_editor):
    Equipamento = apps.get_model("campanha", "Equipamento")
    EfeitoItem = apps.get_model("campanha", "EfeitoItem")

    for nome, (campos, efeitos) in MAPA_EQUIPAMENTO.items():
        atualizados = Equipamento.objects.filter(nome=nome).update(**campos)
        if not atualizados:
            continue  # item não existe neste banco — não interrompe a migração
        for eq in Equipamento.objects.filter(nome=nome):
            for i, ef in enumerate(efeitos):
                EfeitoItem.objects.get_or_create(
                    equipamento=eq, alvo=ef.get("alvo", ""),
                    categoria=ef.get("categoria", "numerico"),
                    defaults=ef,
                )


def reverter_dados(apps, schema_editor):
    Equipamento = apps.get_model("campanha", "Equipamento")
    EfeitoItem = apps.get_model("campanha", "EfeitoItem")

    EfeitoItem.objects.filter(equipamento__nome__in=MAPA_EQUIPAMENTO.keys()).delete()
    for nome in MAPA_EQUIPAMENTO:
        campos, _efeitos = MAPA_EQUIPAMENTO[nome]
        reset = {campo: CAMPOS_RESET[campo] for campo in campos if campo in CAMPOS_RESET}
        Equipamento.objects.filter(nome=nome).update(**reset)


class Migration(migrations.Migration):

    dependencies = [
        ('campanha', '0011_equipamento_efeitos'),
    ]

    operations = [
        migrations.RunPython(migrar_dados, reverter_dados),
    ]
