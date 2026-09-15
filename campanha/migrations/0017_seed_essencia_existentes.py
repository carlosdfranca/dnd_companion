# Backfill do contrato de signals.seed_caracteristicas para personagens que
# já existiam ANTES desta feature: o post_save signal só semeia Essencia em
# `created=True`, então o Rollo (criado muito antes de Essencia existir)
# ficaria sem as 5 linhas. Não é migração de dado real (não há Essencia
# nenhuma no banco ainda) — é só garantir a mesma garantia que todo
# personagem NOVO já ganha automaticamente.

from django.db import migrations


def semear(apps, schema_editor):
    Personagem = apps.get_model("campanha", "Personagem")
    Essencia = apps.get_model("campanha", "Essencia")
    tiers = ["frail", "robust", "potent", "mythic", "deific"]
    for p in Personagem.objects.all():
        for tier in tiers:
            Essencia.objects.get_or_create(personagem=p, tier=tier)


def reverter(apps, schema_editor):
    # Não remove: reverter isso apagaria contadores que o jogador já possa
    # ter preenchido depois de aplicada. Sem-op intencional.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('campanha', '0016_alquimia_harvesting'),
    ]

    operations = [
        migrations.RunPython(semear, reverter),
    ]
