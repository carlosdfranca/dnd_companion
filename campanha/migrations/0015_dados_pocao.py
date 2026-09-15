# Move a única linha real de poção ("Poção de Cura Menor") de Equipamento
# para Pocao. Ela ficou em Equipamento na migração 0012 (Fase 1) porque o
# model Pocao não existia ainda — a fase 2 é quem cria esse lugar certo.
#
# Cura original só como texto legado: "1d4 + 2 de vida ao tomar".
# Parseado à mão (não há parser de expressão de dado no sistema, por
# design): cura_qtd_dados=1, cura_faces=4, cura_bonus=2.

from django.db import migrations

NOME = "Poção de Cura Menor"
TEXTO_LEGADO = "1d4 + 2 de vida ao tomar"


def migrar(apps, schema_editor):
    Equipamento = apps.get_model("campanha", "Equipamento")
    Pocao = apps.get_model("campanha", "Pocao")

    for antigo in Equipamento.objects.filter(nome=NOME):
        Pocao.objects.create(
            personagem_id=antigo.personagem_id,
            nome=antigo.nome,
            quantidade=antigo.quantidade,
            raridade=antigo.raridade,
            peso=antigo.peso,
            lore=antigo.lore,
            cura_qtd_dados=1,
            cura_faces=4,
            cura_bonus=2,
        )
        antigo.delete()


def reverter(apps, schema_editor):
    Equipamento = apps.get_model("campanha", "Equipamento")
    Pocao = apps.get_model("campanha", "Pocao")

    for pocao in Pocao.objects.filter(nome=NOME):
        Equipamento.objects.create(
            personagem_id=pocao.personagem_id,
            nome=pocao.nome,
            tipo="mochila",
            slot=None,
            quantidade=pocao.quantidade,
            raridade=pocao.raridade,
            peso=pocao.peso,
            lore=pocao.lore,
            atributos_efeito_legado=TEXTO_LEGADO,
        )
        pocao.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('campanha', '0014_pocao'),
    ]

    operations = [
        migrations.RunPython(migrar, reverter),
    ]
