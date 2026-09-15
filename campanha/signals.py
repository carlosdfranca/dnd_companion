from django.db.models.signals import post_save
from django.dispatch import receiver

from . import constants
from .models import Personagem, Pericia, Salvaguarda, Essencia


@receiver(post_save, sender=Personagem)
def seed_caracteristicas(sender, instance, created, **kwargs):
    """Ao criar um Personagem, cria as 18 perícias, 6 salvaguardas (não
    proficientes) e as 5 Essencia (quantidade 0).

    Idempotente via get_or_create: seguro mesmo se rodar de novo ou se faltarem linhas.
    """
    if not created:
        return
    for ident, *_ in constants.PERICIAS:
        Pericia.objects.get_or_create(personagem=instance, identificador=ident)
    for ident, *_ in constants.SALVAGUARDAS:
        Salvaguarda.objects.get_or_create(personagem=instance, identificador=ident)
    for ident, _label in constants.ESSENCIAS:
        Essencia.objects.get_or_create(personagem=instance, tier=ident)
