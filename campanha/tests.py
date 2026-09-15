from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from campanha import regras
from campanha.models import (
    Equipamento, EfeitoItem, Personagem, Pocao,
    ComponenteAlquimico, BaseAlquimica, Essencia, ComponenteCriatura,
)


def criar_personagem(**overrides):
    dados = dict(
        nome="Teste", classe="Bárbaro", nivel=5,
        forca=20, destreza=14, constituicao=14,
        inteligencia=10, sabedoria=10, carisma=10,
        bonus_proficiencia=3,
    )
    dados.update(overrides)
    return Personagem.objects.create(**dados)


def equipar(personagem, nome, slot, **campos):
    """Cria um Equipamento já equipado (slot preenchido)."""
    campos.setdefault("quantidade", 1)
    return Equipamento.objects.create(personagem=personagem, nome=nome, slot=slot, **campos)


def efeito(equipamento, alvo, valor, tipo_bonus="", **campos):
    return EfeitoItem.objects.create(
        equipamento=equipamento, categoria="numerico",
        alvo=alvo, valor=valor, tipo_bonus=tipo_bonus, **campos
    )


class CaBaseTests(TestCase):
    def test_desarmado_e_10_mais_destreza(self):
        p = criar_personagem(estilo_ca="desarmado", destreza=14)  # mod +2
        self.assertEqual(regras.ca_calculada(p), 12)

    def test_barbaro_soma_constituicao(self):
        p = criar_personagem(estilo_ca="barbaro", destreza=14, constituicao=14)  # +2 +2
        self.assertEqual(regras.ca_calculada(p), 14)

    def test_armadura_vestida_vence_a_formula_de_classe(self):
        p = criar_personagem(estilo_ca="barbaro", destreza=18, constituicao=18)
        equipar(
            p, "Cota de Malha", "armadura_corporal",
            categoria="armadura", categoria_armadura="media", ca_base_armadura=14,
        )
        # Armadura média: cap de Destreza é +2, mesmo com mod real +4;
        # Defesa sem Armadura do bárbaro NÃO se aplica com armadura vestida.
        self.assertEqual(regras.ca_calculada(p), 16)  # 14 + min(4, 2)

    def test_armadura_pesada_sem_bonus_de_destreza(self):
        p = criar_personagem(estilo_ca="desarmado", destreza=18)
        equipar(
            p, "Armadura de Placas", "armadura_corporal",
            categoria="armadura", categoria_armadura="pesada", ca_base_armadura=18,
        )
        self.assertEqual(regras.ca_calculada(p), 18)  # cap 0: mod de Destreza não soma


class EmpilhamentoTests(TestCase):
    def test_mesmo_tipo_nomeado_nao_empilha_vale_o_maior(self):
        p = criar_personagem(estilo_ca="desarmado", destreza=10)  # base 10
        anel = equipar(p, "Anel de Proteção", "anel_1", magico=True)
        efeito(anel, "ca", 1, tipo_bonus="deflexao")
        capa = equipar(p, "Capa de Proteção", "capa", magico=True)
        efeito(capa, "ca", 3, tipo_bonus="deflexao")  # mesmo tipo, maior valor
        self.assertEqual(regras.ca_calculada(p), 13)  # 10 + max(1, 3), não 10+1+3

    def test_tipos_diferentes_empilham(self):
        p = criar_personagem(estilo_ca="desarmado", destreza=10)
        escudo = equipar(p, "Escudo", "mao_secundaria", categoria="escudo")
        efeito(escudo, "ca", 2, tipo_bonus="escudo")
        capa = equipar(p, "Cloack of Protection", "capa", magico=True)
        efeito(capa, "ca", 1, tipo_bonus="deflexao")
        self.assertEqual(regras.ca_calculada(p), 13)  # 10 + 2 + 1

    def test_bonus_sem_tipo_sempre_soma(self):
        p = criar_personagem(estilo_ca="desarmado", destreza=10)
        a = equipar(p, "Item Encantado A", "anel_1")
        efeito(a, "ca", 1, tipo_bonus="")
        b = equipar(p, "Item Encantado B", "anel_2")
        efeito(b, "ca", 1, tipo_bonus="")
        self.assertEqual(regras.ca_calculada(p), 12)  # 10 + 1 + 1, ambos somam


class GateSintonizacaoTests(TestCase):
    def test_efeito_de_item_nao_sintonizado_nao_conta(self):
        p = criar_personagem(estilo_ca="desarmado", destreza=10)
        capa = equipar(
            p, "Cloack of Protection", "capa",
            magico=True, requer_sintonizacao=True, sintonizado=False,
        )
        efeito(capa, "ca", 1, tipo_bonus="deflexao")
        self.assertEqual(regras.ca_calculada(p), 10)  # efeito desligado

    def test_efeito_liga_ao_sintonizar(self):
        p = criar_personagem(estilo_ca="desarmado", destreza=10)
        capa = equipar(
            p, "Cloack of Protection", "capa",
            magico=True, requer_sintonizacao=True, sintonizado=True,
        )
        efeito(capa, "ca", 1, tipo_bonus="deflexao")
        self.assertEqual(regras.ca_calculada(p), 11)

    def test_item_sem_slot_nao_conta_mesmo_sintonizado(self):
        p = criar_personagem(estilo_ca="desarmado", destreza=10)
        capa = Equipamento.objects.create(
            personagem=p, nome="Cloack de Reserva", slot=None,
            magico=True, requer_sintonizacao=True, sintonizado=True,
        )
        efeito(capa, "ca", 1, tipo_bonus="deflexao")
        self.assertEqual(regras.ca_calculada(p), 10)  # na mochila não conta


class CondicaoTests(TestCase):
    def test_efeito_condicional_nao_soma_por_padrao(self):
        p = criar_personagem(estilo_ca="desarmado", destreza=10)
        amuleto = equipar(p, "Amuleto Anti-Morto-Vivo", "colar")
        efeito(amuleto, "ca", 2, condicao="apenas contra mortos-vivos")
        self.assertEqual(regras.ca_calculada(p), 10)  # situacional, fora da soma

    def test_efeito_condicional_aparece_se_pedido_explicitamente(self):
        p = criar_personagem(estilo_ca="desarmado", destreza=10)
        amuleto = equipar(p, "Amuleto Anti-Morto-Vivo", "colar")
        efeito(amuleto, "ca", 2, condicao="apenas contra mortos-vivos")
        ctx = p.efeitos_ativos
        total = regras.bonus_para(ctx, "ca", incluir_condicionais=True)
        self.assertEqual(total, 2)


class SalvaguardaEIniciativaTests(TestCase):
    def test_bonus_salvaguardas_todas_afeta_qualquer_salvaguarda(self):
        p = criar_personagem(estilo_ca="desarmado")
        capa = equipar(p, "Cloack of Protection", "capa", requer_sintonizacao=True, sintonizado=True)
        efeito(capa, "salvaguardas_todas", 1, tipo_bonus="")
        ctx = p.efeitos_ativos
        self.assertEqual(regras.bonus_para(ctx, "salvaguarda", "destreza"), 1)
        self.assertEqual(regras.bonus_para(ctx, "salvaguarda", "sabedoria"), 1)

    def test_bonus_de_salvaguarda_especifica_nao_vaza_para_outras(self):
        p = criar_personagem(estilo_ca="desarmado")
        anel = equipar(p, "Anel de Evasão", "anel_1")
        efeito(anel, "save_destreza", 2, tipo_bonus="")
        ctx = p.efeitos_ativos
        self.assertEqual(regras.bonus_para(ctx, "salvaguarda", "destreza"), 2)
        self.assertEqual(regras.bonus_para(ctx, "salvaguarda", "sabedoria"), 0)


class RolloIntegracaoTests(TestCase):
    """Reproduz a ficha real de Rollo Stoneblood — o caso de aceite do design:
    CA calculada tem que bater com o valor que estava salvo manualmente (17)."""

    def setUp(self):
        self.p = criar_personagem(
            nome="Rollo Stoneblood", classe="Bárbaro", nivel=5,
            forca=20, destreza=14, constituicao=14,
            inteligencia=12, sabedoria=13, carisma=12,
            bonus_proficiencia=3, estilo_ca="barbaro",
        )
        machado = equipar(
            self.p, "Machado de Batalha", "mao_principal",
            categoria="arma", versatil=True,
            dano_qtd_dados=1, dano_faces=8, dano_faces_versatil=10,
            tipo_dano="cortante", atributo_ataque="forca", proficiente=True,
        )
        escudo = equipar(self.p, "Escudo", "mao_secundaria", categoria="escudo")
        efeito(escudo, "ca", 2, tipo_bonus="escudo")
        capa = equipar(
            self.p, "Cloack of Protection", "capa",
            magico=True, requer_sintonizacao=True, sintonizado=True,
        )
        efeito(capa, "ca", 1, tipo_bonus="deflexao")
        efeito(capa, "salvaguardas_todas", 1, tipo_bonus="")
        self.machado = machado

    def test_ca_calculada_bate_com_o_valor_historico(self):
        self.assertEqual(regras.ca_calculada(self.p), 17)
        self.assertEqual(self.p.ca, 17)  # sem override, cai na calculada

    def test_ca_detalhe_lista_a_composicao(self):
        detalhe = dict(self.p.ca_detalhe)
        self.assertEqual(detalhe["Base"], 14)
        self.assertEqual(detalhe["Escudo"], 2)
        self.assertEqual(detalhe["Cloack of Protection"], 1)

    def test_ataque_derivado_do_machado_bate_com_o_ataque_antigo(self):
        # O antigo model Ataque tinha bonus_atributo=5 (= mod FOR): dano 1d8+5.
        # +8 para acertar = mod FOR (+5) + bônus de proficiência (+3).
        ataques = regras.ataques_do_personagem(self.p)
        self.assertEqual(len(ataques), 1)
        a = ataques[0]
        self.assertEqual(a.nome, "Machado de Batalha")
        self.assertEqual(a.bonus_ataque, 8)
        self.assertEqual(a.formula_dano, "1d8 +5")
        self.assertEqual(a.formula_dano_furia, "1d8 +7")  # bonus_dano_furia default=2
        self.assertEqual(a.tipo_dano, "Cortante")  # rótulo, não o identificador cru
        self.assertTrue(a.versatil)
        self.assertEqual(a.empunhadura_label, "Uma Mão")

    def test_dessintonizar_derruba_ca_e_todas_as_salvaguardas(self):
        capa = Equipamento.objects.get(personagem=self.p, nome="Cloack of Protection")
        capa.sintonizado = False
        capa.save(update_fields=["sintonizado"])
        self.p.__dict__.pop("efeitos_ativos", None)  # invalida o cached_property manualmente

        self.assertEqual(regras.ca_calculada(self.p), 16)  # perde o +1 do cloak
        ctx = self.p.efeitos_ativos
        self.assertEqual(regras.bonus_para(ctx, "salvaguarda", "destreza"), 0)
        self.assertEqual(regras.bonus_para(ctx, "salvaguarda", "sabedoria"), 0)

    def test_arma_versatil_troca_de_dado_ao_empunhar_com_duas_maos(self):
        self.assertEqual(self.machado.dado_dano, "1d8")
        self.machado.empunhadura = "duas"
        self.machado.save(update_fields=["empunhadura"])
        self.assertEqual(self.machado.dado_dano, "1d10")


class EquiparDesequiparTests(TestCase):
    """Cobre o algoritmo de conflito de slots usado pelas actions da UI
    (views.item_equipar/item_desequipar/item_sintonizar/item_empunhadura)."""

    def setUp(self):
        self.p = criar_personagem(estilo_ca="barbaro")

    def test_equipar_slot_livre(self):
        machado = Equipamento.objects.create(
            personagem=self.p, nome="Machado", categoria="arma",
            slot_padrao="mao_principal", versatil=True,
        )
        avisos = regras.equipar(machado)
        machado.refresh_from_db()
        self.assertEqual(avisos, [])
        self.assertEqual(machado.slot, "mao_principal")
        self.assertEqual(machado.tipo, "equipado")

    def test_equipar_duas_maos_desequipa_escudo(self):
        machado = equipar(self.p, "Machado", "mao_principal", categoria="arma", versatil=True)
        escudo = equipar(self.p, "Escudo", "mao_secundaria", categoria="escudo")

        avisos = regras.trocar_empunhadura(machado, "duas")
        escudo.refresh_from_db()

        self.assertEqual(len(avisos), 1)
        self.assertIn("Escudo", avisos[0])
        self.assertIsNone(escudo.slot)

    def test_equipar_escudo_rebaixa_machado_duas_maos_para_uma_mao(self):
        machado = equipar(
            self.p, "Machado", "mao_principal",
            categoria="arma", versatil=True, empunhadura="duas",
        )
        escudo = Equipamento.objects.create(
            personagem=self.p, nome="Escudo", categoria="escudo", slot=None,
        )

        avisos = regras.equipar(escudo, slot_alvo="mao_secundaria")
        machado.refresh_from_db()
        escudo.refresh_from_db()

        self.assertEqual(len(avisos), 1)
        self.assertIn("uma mão", avisos[0])
        self.assertEqual(machado.empunhadura, "uma")
        self.assertEqual(machado.slot, "mao_principal")  # continua equipado
        self.assertEqual(escudo.slot, "mao_secundaria")

    def test_arma_duas_maos_inerente_ocupa_as_duas_maos_sempre(self):
        arco = Equipamento.objects.create(
            personagem=self.p, nome="Arco Longo", categoria="arma",
            duas_maos=True, slot=None,
        )
        avisos = regras.equipar(arco, slot_alvo="mao_principal")
        arco.refresh_from_db()
        self.assertEqual(avisos, [])
        self.assertEqual(arco.empunhadura, "duas")
        self.assertEqual(set(arco.slots_ocupados), {"mao_principal", "mao_secundaria"})

    def test_arma_duas_maos_solta_em_mao_secundaria_normaliza_para_principal(self):
        arco = Equipamento.objects.create(
            personagem=self.p, nome="Arco Longo", categoria="arma",
            duas_maos=True, slot=None,
        )
        regras.equipar(arco, slot_alvo="mao_secundaria")
        arco.refresh_from_db()
        self.assertEqual(arco.slot, "mao_principal")
        self.assertEqual(set(arco.slots_ocupados), {"mao_principal", "mao_secundaria"})

    def test_desequipar_nao_quebra_sintonizacao(self):
        capa = Equipamento.objects.create(
            personagem=self.p, nome="Capa", categoria="acessorio",
            slot="capa", requer_sintonizacao=True, sintonizado=True,
        )
        regras.desequipar(capa)
        capa.refresh_from_db()
        self.assertIsNone(capa.slot)
        self.assertTrue(capa.sintonizado)  # só dessintonizar() muda isso

    def test_sintonizar_respeita_limite(self):
        itens = [
            Equipamento.objects.create(
                personagem=self.p, nome=f"Mágico {i}", requer_sintonizacao=True, slot=None,
            )
            for i in range(4)
        ]
        for item in itens[:3]:
            regras.sintonizar(item)
        with self.assertRaises(ValidationError):
            regras.sintonizar(itens[3])
        self.assertEqual(
            Equipamento.objects.filter(personagem=self.p, sintonizado=True).count(), 3
        )

    def test_sintonizar_item_que_nao_exige_falha(self):
        corda = Equipamento.objects.create(personagem=self.p, nome="Corda", slot=None)
        with self.assertRaises(ValidationError):
            regras.sintonizar(corda)

    def test_gate_liga_apos_sintonizar_e_desliga_apos_dessintonizar(self):
        capa = Equipamento.objects.create(
            personagem=self.p, nome="Capa", slot="capa", requer_sintonizacao=True,
        )
        efeito(capa, "ca", 1, tipo_bonus="deflexao")

        self.assertFalse(capa.efeitos_habilitados)
        regras.sintonizar(capa)
        capa.refresh_from_db()
        self.assertTrue(capa.efeitos_habilitados)

        regras.dessintonizar(capa)
        capa.refresh_from_db()
        self.assertFalse(capa.efeitos_habilitados)

    def test_trocar_empunhadura_recusa_se_nao_for_versatil(self):
        adaga = Equipamento.objects.create(
            personagem=self.p, nome="Adaga", categoria="arma", slot="mao_principal",
        )
        with self.assertRaises(ValidationError):
            regras.trocar_empunhadura(adaga, "duas")


class PocaoTests(TestCase):
    def setUp(self):
        self.p = criar_personagem(pv_maximo=20, pv_atual=10, pv_temporario=0)

    def _pocao(self, **overrides):
        dados = dict(
            personagem=self.p, nome="Poção de Cura Menor",
            quantidade=1, cura_qtd_dados=1, cura_faces=4, cura_bonus=2,
        )
        dados.update(overrides)
        return Pocao.objects.create(**dados)

    def test_cura_soma_ao_pv(self):
        pocao = self._pocao()
        regras.aplicar_pocao(pocao, cura_forcada=3)  # 1d4 forçado em 3 => 3+2=5
        self.p.refresh_from_db()
        self.assertEqual(self.p.pv_atual, 15)

    def test_cura_nao_ultrapassa_pv_maximo(self):
        self.p.pv_atual = 18
        self.p.save(update_fields=["pv_atual"])
        pocao = self._pocao(quantidade=2)
        regras.aplicar_pocao(pocao, cura_forcada=4)  # 4+2=6, estouraria 24
        self.p.refresh_from_db()
        self.assertEqual(self.p.pv_atual, 20)  # teto em pv_maximo

    def test_quantidade_decrementa_sem_remover(self):
        pocao = self._pocao(quantidade=3)
        regras.aplicar_pocao(pocao, cura_forcada=1)
        pocao.refresh_from_db()
        self.assertEqual(pocao.quantidade, 2)
        self.assertTrue(Pocao.objects.filter(pk=pocao.pk).exists())

    def test_remove_da_lista_ao_chegar_a_zero(self):
        pocao = self._pocao(quantidade=1)
        pk = pocao.pk
        regras.aplicar_pocao(pocao, cura_forcada=1)
        self.assertFalse(Pocao.objects.filter(pk=pk).exists())

    def test_efeito_adicional_automatizado_aplica_pv_temporario(self):
        pocao = self._pocao(
            nome="Elixir de Vigor", efeito_categoria="pv_temporario", efeito_valor=5,
        )
        avisos = regras.aplicar_pocao(pocao, cura_forcada=1)
        self.p.refresh_from_db()
        self.assertEqual(self.p.pv_temporario, 5)
        self.assertTrue(any("PV temporário" in a for a in avisos))

    def test_efeito_adicional_nao_automatizado_vira_aviso_sem_mudar_estado(self):
        pocao = self._pocao(
            nome="Poção de Resistência ao Fogo",
            efeito_categoria="resistencia_buff", efeito_alvo="fogo", efeito_valor=0,
        )
        avisos = regras.aplicar_pocao(pocao, cura_forcada=1)
        self.p.refresh_from_db()
        self.assertEqual(self.p.pv_temporario, 0)  # nada automatizado mudou
        self.assertTrue(any("manualmente" in a for a in avisos))

    def test_rolar_cura_fica_dentro_do_intervalo_do_dado(self):
        pocao = self._pocao(cura_qtd_dados=2, cura_faces=4, cura_bonus=1)
        for _ in range(50):
            rolado, cura = regras.rolar_cura(pocao)
            self.assertGreaterEqual(rolado, 2)
            self.assertLessEqual(rolado, 8)
            self.assertEqual(cura, rolado + 1)

    def test_carga_total_inclui_pocoes(self):
        self._pocao(peso="0.25", quantidade=4)
        self.assertEqual(regras.carga_total(self.p), Decimal("1.00"))


class AlquimiaHarvestingTests(TestCase):
    """Alquimia (ComponenteAlquimico/BaseAlquimica) e Harvesting
    (Essencia/ComponenteCriatura) — armazenamento puro, sem motor de regras."""

    def setUp(self):
        self.p = criar_personagem()

    def test_criar_componente_alquimico(self):
        c = ComponenteAlquimico.objects.create(
            personagem=self.p, nome="Folha de Sombra", reagente="trevas", quantidade=3,
        )
        self.assertEqual(c.reagente, "trevas")
        self.assertEqual(c.quantidade, 3)

    def test_criar_base_alquimica(self):
        b = BaseAlquimica.objects.create(personagem=self.p, nome="Óleo Base", quantidade=2)
        self.assertEqual(b.quantidade, 2)
        self.assertFalse(hasattr(b, "reagente"))  # BaseAlquimica não tem reagente

    def test_criar_componente_criatura(self):
        c = ComponenteCriatura.objects.create(
            personagem=self.p, nome="Garra de Dragão", tipo_origem="dragon", quantidade=1,
        )
        self.assertEqual(c.tipo_origem, "dragon")

    def test_carga_total_soma_alquimia_e_harvesting(self):
        ComponenteAlquimico.objects.create(
            personagem=self.p, nome="Folha", reagente="fogo", peso=Decimal("0.10"), quantidade=5,
        )
        BaseAlquimica.objects.create(
            personagem=self.p, nome="Óleo", peso=Decimal("0.50"), quantidade=2,
        )
        ComponenteCriatura.objects.create(
            personagem=self.p, nome="Garra", tipo_origem="beast", peso=Decimal("0.20"), quantidade=3,
        )
        # 0.10*5 + 0.50*2 + 0.20*3 = 0.50 + 1.00 + 0.60 = 2.10
        self.assertEqual(regras.carga_total(self.p), Decimal("2.10"))

    def test_essencia_seed_signal_cria_5_tiers_com_zero(self):
        # criar_personagem() já dispara o signal (post_save, created=True).
        essencias = Essencia.objects.filter(personagem=self.p).order_by("tier")
        self.assertEqual(essencias.count(), 5)
        self.assertTrue(all(e.quantidade == 0 for e in essencias))
        tiers = set(essencias.values_list("tier", flat=True))
        self.assertEqual(tiers, {"frail", "robust", "potent", "mythic", "deific"})

    def test_essencia_nao_conta_na_carga(self):
        essencia = Essencia.objects.get(personagem=self.p, tier="mythic")
        essencia.quantidade = 999
        essencia.save(update_fields=["quantidade"])
        self.assertEqual(regras.carga_total(self.p), 0)  # sem peso, não soma

    def test_essencia_unique_constraint_por_personagem_e_tier(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Essencia.objects.create(personagem=self.p, tier="frail", quantidade=1)


class CentralCombateViewTests(TestCase):
    """Testes de view (via Client) do card Ataques/Dano na Central de Combate
    — pegam exatamente o tipo de bug que passa batido em teste unitário de
    regras.py: nome de campo errado no template renderiza em branco sem erro,
    e uma relação apagada (`p.ataques`) só quebra quando a view é executada."""

    def setUp(self):
        self.p = criar_personagem(pv_maximo=20, pv_atual=15, estilo_ca="barbaro")
        equipar(
            self.p, "Machado de Batalha", "mao_principal",
            categoria="arma", versatil=True,
            dano_qtd_dados=1, dano_faces=8, dano_faces_versatil=10,
            tipo_dano="cortante", atributo_ataque="forca", proficiente=True,
        )

    def test_central_combate_mostra_ataque_da_arma_equipada(self):
        resp = self.client.get(reverse("combate"))
        self.assertEqual(resp.status_code, 200)
        conteudo = resp.content.decode("utf-8")
        self.assertIn("Machado de Batalha", conteudo)
        self.assertIn("1d8", conteudo)  # a fórmula tem que aparecer, não em branco

    def test_descanso_longo_via_ajax_nao_quebra_mais(self):
        # Regressão: _descanso_ajax_response ainda chamava p.ataques.all(),
        # uma relação que não existe mais desde que o model Ataque foi
        # removido — dava 500 em todo descanso longo disparado via AJAX.
        resp = self.client.post(
            reverse("descanso", args=["longo"]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertIn("Machado de Batalha", data["ataques_html"])
