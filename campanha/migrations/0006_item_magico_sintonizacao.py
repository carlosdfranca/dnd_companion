from django.db import migrations, models


def migrar_tipo_magico(apps, schema_editor):
    """Itens com o antigo tipo 'magico' viram tipo='mochila' + magico=True."""
    ItemInventario = apps.get_model("campanha", "ItemInventario")
    ItemInventario.objects.filter(tipo="magico").update(tipo="mochila", magico=True)


def reverter_tipo_magico(apps, schema_editor):
    ItemInventario = apps.get_model("campanha", "ItemInventario")
    ItemInventario.objects.filter(magico=True, tipo="mochila").update(tipo="magico")


class Migration(migrations.Migration):

    dependencies = [
        ("campanha", "0005_nota_combate"),
    ]

    operations = [
        migrations.AddField(
            model_name="iteminventario",
            name="magico",
            field=models.BooleanField(default=False, verbose_name="Item Mágico"),
        ),
        migrations.AddField(
            model_name="iteminventario",
            name="requer_sintonizacao",
            field=models.BooleanField(
                default=False,
                help_text="Itens sintonizados não podem ser trocados livremente (exige descanso).",
                verbose_name="Requer Sintonização",
            ),
        ),
        migrations.RunPython(migrar_tipo_magico, reverter_tipo_magico),
        migrations.AlterField(
            model_name="iteminventario",
            name="tipo",
            field=models.CharField(
                choices=[("equipado", "Equipado"), ("mochila", "Mochila")],
                default="mochila",
                max_length=10,
                verbose_name="Localização",
            ),
        ),
    ]
