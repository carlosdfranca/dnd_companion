# Fecha o Fase 1 do sistema de itens estruturado:
#   1. Define `estilo_ca` = "barbaro" para Rollo (Defesa sem Armadura) e limpa
#      `ca_override` — a partir daqui a CA passa a ser CALCULADA, não digitada.
#      Só limpamos o override quando ele bate com o valor conhecido calculado
#      à mão para este personagem (17 = base 14 + escudo 2 + cloak 1); não dá
#      para chamar `regras.ca_calculada` de dentro de uma migração porque
#      `apps.get_model` devolve um model histórico, sem as properties custom.
#   2. Troca `slot=""` por `slot=NULL` nas linhas existentes — consequência
#      do AlterField abaixo, que faz `slot` aceitar NULL (ver nota em
#      models.py: é a forma nativa do MySQL de ter unicidade condicional).
#   3. Adiciona a UniqueConstraint de slot único por personagem, agora que os
#      dados estão corretos (deferida desde 0011 de propósito, para uma
#      violação de constraint apontar bug de DADO, não confusão de ordem
#      schema/dado).

from django.db import migrations, models


def ajustar_ca(apps, schema_editor):
    Personagem = apps.get_model("campanha", "Personagem")
    Personagem.objects.filter(classe="Bárbaro").update(estilo_ca="barbaro")

    # Rollo Stoneblood, Bárbaro 5, DES 14 (mod +2), CON 14 (mod +2):
    # base Defesa sem Armadura = 10+2+2 = 14; + Escudo (+2 tipo "escudo")
    # + Cloack of Protection (+1 tipo "deflexao") = 17. Bate com o
    # ca_override armazenado (17) — pode ser limpo com segurança.
    Personagem.objects.filter(nome="Rollo Stoneblood", ca_override=17).update(ca_override=None)


def reverter_ca(apps, schema_editor):
    Personagem = apps.get_model("campanha", "Personagem")
    Personagem.objects.filter(nome="Rollo Stoneblood", ca_override__isnull=True).update(
        ca_override=17,
    )
    Personagem.objects.filter(classe="Bárbaro").update(estilo_ca="desarmado")


def slot_vazio_para_null(apps, schema_editor):
    Equipamento = apps.get_model("campanha", "Equipamento")
    Equipamento.objects.filter(slot="").update(slot=None)


def slot_null_para_vazio(apps, schema_editor):
    Equipamento = apps.get_model("campanha", "Equipamento")
    Equipamento.objects.filter(slot__isnull=True).update(slot="")


class Migration(migrations.Migration):

    dependencies = [
        ('campanha', '0012_dados_equipamento'),
    ]

    operations = [
        migrations.RunPython(ajustar_ca, reverter_ca),

        # slot vira NULL-capaz ANTES de converter os dados existentes.
        migrations.AlterField(
            model_name='equipamento',
            name='slot',
            field=models.CharField(
                blank=True, null=True, default=None, max_length=20,
                choices=[
                    ('mao_principal', 'Mão Principal'), ('mao_secundaria', 'Mão Secundária'),
                    ('armadura_corporal', 'Armadura Corporal'), ('capa', 'Capa / Manto'),
                    ('cabeca', 'Cabeça'), ('colar', 'Colar / Amuleto'), ('cinto', 'Cinto'),
                    ('anel_1', 'Anel 1'), ('anel_2', 'Anel 2'), ('luvas', 'Luvas'),
                    ('botas', 'Botas'), ('municao', 'Munição'),
                ],
                help_text='Em branco = na mochila.', verbose_name='Slot equipado',
            ),
        ),
        migrations.RunPython(slot_vazio_para_null, slot_null_para_vazio),

        migrations.AddConstraint(
            model_name='equipamento',
            constraint=models.UniqueConstraint(
                fields=('personagem', 'slot'), name='uniq_equipamento_slot_personagem',
            ),
        ),
    ]
