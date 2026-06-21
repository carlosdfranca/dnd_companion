from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),

    # Ficha
    path("ficha/", views.ficha, name="ficha"),
    path("ficha/editar/", views.FichaEditView.as_view(), name="ficha_editar"),

    # Central de Combate
    path("combate/", views.central_combate, name="combate"),
    path("combate/pv/", views.atualizar_pv, name="pv_atualizar"),
    path("combate/descanso/curto/dados/", views.descanso_curto_dados, name="descanso_curto_dados"),
    path("combate/descanso/<str:tipo>/", views.aplicar_descanso, name="descanso"),
    path("combate/recurso/<int:pk>/usar/", views.usar_recurso, name="recurso_usar"),
    path("combate/recurso/<int:pk>/restaurar/", views.restaurar_recurso, name="recurso_restaurar"),

    # Notas de Combate
    path("combate/notas/nova/", views.NotaCombateCreateView.as_view(), name="nota_create"),
    path("combate/notas/<int:pk>/editar/", views.NotaCombateUpdateView.as_view(), name="nota_update"),
    path("combate/notas/<int:pk>/excluir/", views.NotaCombateDeleteView.as_view(), name="nota_delete"),

    # Itens
    path("itens/", views.ItemListView.as_view(), name="item_list"),
    path("itens/novo/", views.ItemCreateView.as_view(), name="item_create"),
    path("itens/<int:pk>/editar/", views.ItemUpdateView.as_view(), name="item_update"),
    path("itens/<int:pk>/excluir/", views.ItemDeleteView.as_view(), name="item_delete"),

    # Recursos
    path("recursos/", views.RecursoListView.as_view(), name="recurso_list"),
    path("recursos/novo/", views.RecursoCreateView.as_view(), name="recurso_create"),
    path("recursos/<int:pk>/editar/", views.RecursoUpdateView.as_view(), name="recurso_update"),
    path("recursos/<int:pk>/excluir/", views.RecursoDeleteView.as_view(), name="recurso_delete"),

    # Locais
    path("locais/", views.LocalListView.as_view(), name="local_list"),
    path("locais/novo/", views.LocalCreateView.as_view(), name="local_create"),
    path("locais/<int:pk>/", views.LocalDetailView.as_view(), name="local_detail"),
    path("locais/<int:pk>/editar/", views.LocalUpdateView.as_view(), name="local_update"),
    path("locais/<int:pk>/excluir/", views.LocalDeleteView.as_view(), name="local_delete"),

    # NPCs
    path("npcs/", views.NPCListView.as_view(), name="npc_list"),
    path("npcs/novo/", views.NPCCreateView.as_view(), name="npc_create"),
    path("npcs/<int:pk>/", views.NPCDetailView.as_view(), name="npc_detail"),
    path("npcs/<int:pk>/editar/", views.NPCUpdateView.as_view(), name="npc_update"),
    path("npcs/<int:pk>/excluir/", views.NPCDeleteView.as_view(), name="npc_delete"),

    # Missões
    path("missoes/", views.MissaoListView.as_view(), name="missao_list"),
    path("missoes/nova/", views.MissaoCreateView.as_view(), name="missao_create"),
    path("missoes/<int:pk>/", views.MissaoDetailView.as_view(), name="missao_detail"),
    path("missoes/<int:pk>/editar/", views.MissaoUpdateView.as_view(), name="missao_update"),
    path("missoes/<int:pk>/excluir/", views.MissaoDeleteView.as_view(), name="missao_delete"),
    path("missoes/<int:pk>/concluir/", views.concluir_missao, name="missao_concluir"),

    # Sessões
    path("sessoes/", views.SessaoListView.as_view(), name="sessao_list"),
    path("sessoes/nova/", views.SessaoCreateView.as_view(), name="sessao_create"),
    path("sessoes/<int:pk>/", views.SessaoDetailView.as_view(), name="sessao_detail"),
    path("sessoes/<int:pk>/editar/", views.SessaoUpdateView.as_view(), name="sessao_update"),
    path("sessoes/<int:pk>/excluir/", views.SessaoDeleteView.as_view(), name="sessao_delete"),

    # Informações
    path("infos/nova/", views.InfoCreateView.as_view(), name="info_create"),
    path("infos/<int:pk>/excluir/", views.InfoDeleteView.as_view(), name="info_delete"),
]
