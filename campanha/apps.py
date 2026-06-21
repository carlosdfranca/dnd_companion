from django.apps import AppConfig


class CampanhaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'campanha'
    verbose_name = 'Campanha'

    def ready(self):
        from . import signals  # noqa: F401  (registra os signals)
