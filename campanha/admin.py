from django.contrib import admin

from .models import (
    Personagem,
    Pericia,
    Salvaguarda,
    RecursoDeCombate,
    Equipamento,
    EfeitoItem,
    Local,
    NPC,
    Missao,
    ResumoSessao,
    InformacaoImportante,
)


class PericiaInline(admin.TabularInline):
    model = Pericia
    extra = 0


class SalvaguardaInline(admin.TabularInline):
    model = Salvaguarda
    extra = 0


class RecursoInline(admin.TabularInline):
    model = RecursoDeCombate
    extra = 0


class ItemInline(admin.TabularInline):
    model = Equipamento
    extra = 0


@admin.register(Personagem)
class PersonagemAdmin(admin.ModelAdmin):
    list_display = ("nome", "raca", "classe", "nivel", "pv_atual", "pv_maximo", "ca")
    inlines = [SalvaguardaInline, PericiaInline, RecursoInline, ItemInline]


@admin.register(RecursoDeCombate)
class RecursoDeCombateAdmin(admin.ModelAdmin):
    list_display = ("nome", "personagem", "usos_restantes", "usos_totais", "recuperacao")
    list_filter = ("recuperacao", "personagem")


class EfeitoItemInline(admin.TabularInline):
    model = EfeitoItem
    extra = 1


@admin.register(Equipamento)
class EquipamentoAdmin(admin.ModelAdmin):
    list_display = ("nome", "personagem", "slot", "categoria", "sintonizado", "quantidade")
    list_filter = ("categoria", "slot", "personagem")
    search_fields = ("nome",)
    inlines = [EfeitoItemInline]


@admin.register(Local)
class LocalAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo", "status")
    list_filter = ("tipo",)
    search_fields = ("nome",)


@admin.register(NPC)
class NPCAdmin(admin.ModelAdmin):
    list_display = ("nome", "local", "relacao_grupo")
    list_filter = ("relacao_grupo", "local")
    search_fields = ("nome",)


@admin.register(Missao)
class MissaoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "status")
    list_filter = ("status",)
    search_fields = ("titulo",)


@admin.register(ResumoSessao)
class ResumoSessaoAdmin(admin.ModelAdmin):
    list_display = ("numero", "titulo", "data")


@admin.register(InformacaoImportante)
class InformacaoImportanteAdmin(admin.ModelAdmin):
    list_display = ("texto", "missao", "npc")


# Perícias e salvaguardas também avulsas, caso necessário
admin.site.register(Pericia)
admin.site.register(Salvaguarda)

admin.site.site_header = "Belmora Tracker — Administração"
admin.site.site_title = "Belmora Tracker"
admin.site.index_title = "Campanha"
