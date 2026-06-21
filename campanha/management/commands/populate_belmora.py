"""
Carga inicial idempotente da campanha de Belmora.
Pode ser executado múltiplas vezes sem duplicar dados.

Uso:
    python manage.py populate_belmora
"""

from django.core.management.base import BaseCommand
from django.db.models import F

from campanha.models import (
    InformacaoImportante,
    ItemInventario,
    Local,
    Missao,
    NPC,
    Personagem,
    Pericia,
    RecursoDeCombate,
    ResumoSessao,
    Salvaguarda,
)

BACKGROUND_ROLLO = """\
Rollo Stoneblood cresceu no Eira Djupt — "Pedra Funda" —, um acampamento goliath num vale \
estreito da montanha. Cem anos antes, um ancestral chamado Torstein salvou os sobreviventes \
de um ataque e os guiou até ali. Desde então o acampamento carrega essa dívida de exílio e \
lealdade.

Seu pai Brenn contava histórias de Torstein enquanto afiava ferramentas; sua mãe Sigra \
transformava qualquer dificuldade em lição antes que Rollo tivesse tempo de reclamar. O \
treino físico veio de Dagna — velha como montanha, sem título, implacável. O treino interior \
veio de Halvard, o mais velho do acampamento, cujo bisavô esteve no túnel onde Torstein \
carregou os últimos sobreviventes.

Halvard ensinou que a fúria goliath não é só raiva: é acesso à Árvore do Mundo, uma \
estrutura que conecta os planos. Quando se entra em fúria do jeito certo, a força vital da \
Árvore passa pelo bárbaro e vai para quem ele quer proteger. Na parede mais funda da pedra \
havia um sulco ramificado como raízes — ou relâmpago parado. Uma raiz real da Árvore.

Rollo deixou o acampamento para descobrir o que significa proteger além das montanhas. \
Encontrou o grupo e fundou o Escudo de Belmora.\
"""

# Resumos completos das sessões
SESSOES = [
    (
        1,
        "O Nascimento do Escudo",
        """\
Reunidos ao redor de uma fogueira, o grupo decidiu abandonar as antigas guildas e criar \
algo novo: o Escudo de Belmora. Foram até uma vila para oficializar a guilda, mas o \
reconhecimento só viria após uma missão. Escolheram a missão da Filha Desaparecida, \
porém uma guilda rival reivindicou o direito. A disputa foi resolvida em cinco provas — \
vitória do grupo por 3x2.

Como a investigação levaria até Aella (3 dias de viagem) e o grupo não tinha recursos, \
priorizaram o caso do Espírito Mascarado, vindo de Enzam. No caminho, uma figura mascarada \
surgiu retirando de dentro de uma mulher um vulto negro e o guardando numa bolsa. Ao \
perceber o grupo, apenas os observou e desapareceu. O vulto restante ganhou forma — corpo de \
sombras e cabeça de caveira — e atacou. Beren finalizou a criatura.

A mulher despertou indignada: "Por que fizeram isso? Eu precisava disso…" — transformando \
completamente o significado da ação do grupo.\
""",
    ),
    (
        2,
        "O Espírito Mascarado",
        """\
O grupo chegou à vila de Enzam, ainda em reconstrução após um incêndio. O padre Harkan \
explicou: nas semanas após o incêndio, pessoas em luto passaram a agir de forma estranha — \
algumas excessivamente felizes, outras completamente apáticas. Uma entidade chamada Yokai \
(o "Coletor de Pesares") estava removendo a negatividade das pessoas, mas algo estava errado \
nesse equilíbrio.

A mulher Amara afirmava que o Yokai estava ajudando, não prejudicando. Os halflings Harkin e \
Durgan não conseguiam explicar como chegaram ao estado atual. O grupo encontrou o Yokai, que \
invocou sombras das próprias vítimas. Conseguiram derrotar as sombras, mas o Yokai escapou.

De volta à vila, as sombras retornaram aos hospedeiros e o casal de halflings entrou em \
colapso emocional, revelando o luto pela perda de um filho no incêndio. Com ajuda de Harkan, \
o grupo realizou um exorcismo e libertou os halflings. Na segunda tentativa, o Yokai foi \
derrotado definitivamente. A missão foi concluída com recompensa.\
""",
    ),
    (
        3,
        "Os Caminhos até Helindor",
        """\
De volta a Ravenshire, o grupo descobriu que o poder político da cidade estava com Lirion, \
o Duque. Oficializaram o Escudo de Belmora no quartel. O ferreiro Fyllas era especializado \
em armas e armaduras; o armadilheiro Ferb avaliou os itens da missão anterior. Na loja de \
itens mágicos adquiriram uma Bag of Holding.

Lirion convocou o grupo: uma ilha chamada Heliodor estava isolada há muito tempo, abrigando \
a base da Igreja da Lua, famosa por curas milagrosas. Um evento chamado "Redenção" estava \
atraindo enfermos de todo lugar. O duque forneceu provisões e indicou um barco em Kilmena.

O grupo escolheu o caminho mais seguro. No trajeto, enfrentou três ogros — dominados sem \
dificuldade. Beren e Órun erraram ao comer a sopa dos ogros e sofreram intoxicação alimentar \
severa. Numa ponte bloqueada por um goblin, resolveram três enigmas para passar. O goblin \
correu entusiasmado para o acampamento dos ogros quando mencionaram a comida disponível. O \
grupo chegou a Kilmena.\
""",
    ),
    (
        4,
        "Redenção de Helindor",
        """\
O grupo chegou à ilha de Helindor, fria de forma anormal para sua localização. Um guarda os \
conduziu ao convés superior do navio. O navio era dividido em três níveis: feridos graves \
(inferior), doentes (intermediário) e demais (superior). Casacos foram distribuídos — exceto \
para Rollo, cuja resistência goliath tornava desnecessário.

Na ilha, pessoas de múltiplas nações se acumulavam pelas ruas enquanto figuras encapuzadas \
da Igreja da Lua distribuíam comida. Irmão Liam recebeu o grupo calorosamente. Beren e Órun \
investigaram magicamente o ensopado distribuído: Beren detectou encantamento por toda a ilha; \
Órun identificou uma força manipulando a mente das pessoas.

A mulher Reika (Igreja de Tyr) guiou o grupo para uma casa afastada e revelou: quem comia \
o ensopado ficava vazio, sem identidade. Ela suspeitava que a Igreja da Lua causou o incêndio \
que matou seu marido. O grupo aceitou a sopa de Reika (feita com flores medicinais do bosque).

O grupo investigou o bosque. Depois de combater criaturas e sem encontrar as flores, voltou \
para a Redenção. Glint, o curandeiro, curou instantaneamente uma jovem debilitada — mas então \
iniciou um ritual sombrio, invocando um demônio gigantesco e quatro criaturas menores. Rollo \
assumiu a linha de frente contra o demônio principal enquanto os outros lidavam com os menores. \
Victoria. Rollo correu atrás de Glint — que estava escondido, aterrorizado e confuso sobre o \
que havia acontecido.\
""",
    ),
    (
        5,
        "O Preço da Ganância",
        """\
Após a batalha, Glint estava desacordado com um ferimento nas costas. Lyssandra o estabilizou. \
Quando acordou, estava assustado e confuso — parecia não ter planejado o que aconteceu.

Na Igreja da Lua abandonada, Órun encontrou um bilhete: "Sigam o caminho da cripta de \
Bharomil." Glint explicou: maior cripta do cemitério. Antes de seguir, foram encontrar Reika \
— ela estava finalizando um demônio sozinha. Após descanso, desceram para as ruínas escondidas \
dentro de uma montanha.

Na entrada: escrita em língua gigante — "Maças Nevascas, bem-vindos. Quebradores de Pedras \
não são bem-vindos." Salão gigantesco, alavanca, ossos triturados. Ativaram uma armadilha (pedras \
caindo) mas ninguém foi atingido. Mais adiante: ambiente de lar gigante, gigantes congelados, \
mesas enormes. Uma porta exigia uma palavra. Resposta: "Gelo."

Dentro: pessoas presas em jaulas enquanto uma warlock sugava sua energia. Combate brutal — \
três do grupo foram derrubados, Lyssandra quase morreu. Vitória. Os prisioneiros foram \
libertados. Mais adiante: salão dos tronos, dois gigantes congelados. Entre eles, um cubo.

O grupo pegou o cubo. Erro.

O gelo começou a quebrar. Os gigantes despertaram. Fugiram pelos corredores — outros gigantes \
acordando pelo caminho. As pessoas que acabaram de salvar morreram enquanto fugiam. O grupo \
avisou quem pôde, correu pelo cemitério, pela cidade, até o barco com Reika. Conseguiram fugir. \
Helindor ficou para trás em destruição.\
""",
    ),
    (
        6,
        "Ecos de um Império Caído",
        """\
No navio de volta a Ravenshire, Lyssandra estava desacordada. O médico priorizava os \
sobreviventes mais graves — o grupo ajudou com os feridos. Ao chegar ao porto, guardas os \
esperavam: Lorde Lyrion queria respostas.

O grupo relatou a Igreja da Lua, Glint, os demônios e a destruição — mas omitiu o cubo. \
Disseram que os gigantes despertaram quando libertaram os prisioneiros. Quando mencionaram \
as palavras de Glint durante o ritual, Lyrion reconheceu: Abyssal, a língua dos demônios. \
Mesmo assim, cumpriu sua promessa: o Escudo de Belmora recebeu terras.

Na cidade: venderam materiais com Ferb, descobriram que a espada encontrada na cripta era \
de aço valyriano — precisaria do mestre ferreiro de Novigrad para ser restaurada. A loja de \
poções estava abandonada. João (atendente da guilda) e Maria (filha de Madalena) anunciariam \
casamento. Lyrion enviou a bandeira da guilda e uma carroça com dois cavalos.

No dia seguinte, nas novas terras, ergueram a bandeira pela primeira vez. Lyrion apareceu e \
revelou a história completa do continente: Sylvaris unificou tudo, caiu sem sucessores claros. \
Agora quatro forças disputam o legado — Elyndor (Valcarys), Vysania (Reino Umbral), Aelar \
(Novigrad), Seris. Todos buscam a pesquisa de Sylvaris: O Núcleo.

Lyrion revelou também os Custódios — 12 guerreiros de elite jurados a Sylvaris, libertos após \
sua queda, desaparecidos. Última pista: extremo sul, 42 anos atrás. Missão: encontrá-los \
antes dos outros, impedir que qualquer força os use. Lyssandra revelou sua missão: recuperar \
um Ovo de Dragão roubado por Sylvaris.

O grupo mostrou o cubo a Lyrion. Ele tentou ativá-lo e congelou o lago próximo. Disse já ter \
visto artefatos assim — objetos que agem por vontade própria. Pediu que levassem o cubo para \
Tharn, na Floresta de Valen.\
""",
    ),
    (
        7,
        "Floresta de Valen",
        """\
Lyrion foi embora. O grupo decidiu ir à Floresta de Valen encontrar Tharn. Deixaram carroça \
e cavalos no acampamento e caminharam 3 horas até a floresta. Tentaram entrar em silêncio, \
sem sucesso em encontrar um caminho — mas sentiam que estavam sendo vigiados.

Beren avistou um cervo completamente branco. Sem magia detectável, o cervo começou a se \
afastar trotando e eventualmente sumiu. Acamparam ali. De manhã, viram javalis com musgo e \
flores nas costas — saudáveis, não doentes. Órun subiu numa árvore e avistou formas a leste.

As "estátuas" eram árvores que imitavam formas humanoides. Uma pedra entalhada dizia \
"escute". Ao prestar atenção, ouviram madeira se movendo ao longe — aumentando gradualmente. \
Lyssandra escutou uma conversa na floresta. Quando foram investigar, criaturas (homens-árvore) \
atacaram. Derrotaram os monstros.

O cervo branco apareceu. Debate sobre seguir ou não. Beren e Lyssandra foram atrás — \
encontraram uma árvore gigante com uma porta. Chamaram Rollo e Órun. Dentro da árvore havia \
uma escada. Subiram e encontraram Tharn, o Casco Antigo.

Tharn removeu o selo da carta misteriosa. Era uma carta de amor escrita por Elyra (uma elfa \
que abriu mão da imortalidade) para Bharomil (um Custódio) — descrevendo a paz que encontraram \
em Helindor, mencionando raízes gigantescas encontradas sob a montanha que pulsavam como se a \
terra respirasse, e esperando que os gigantes continuassem dormindo.

Sobre o cubo: Tharn explicou que artefatos com magia por tempo suficiente desenvolvem vontade \
própria. O cubo provavelmente congelou os gigantes porque queria isso. Para descobrir sua \
finalidade, precisariam ir mais fundo em Helindor. O anel de Lyssandra (da warlock) também \
teria vontade própria. Os homens-árvore provavelmente atacaram porque alguém veio à floresta \
com más intenções — não por causa do grupo.\
""",
    ),
]


class Command(BaseCommand):
    help = "Carrega dados reais da campanha de Belmora (idempotente)"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== Populando banco de dados — Belmora ===\n"))

        personagem = self._criar_personagem()
        self._configurar_proficiencias(personagem)
        self._criar_recursos(personagem)
        self._criar_inventario(personagem)
        locais = self._criar_locais()
        npcs = self._criar_npcs(locais)
        missoes = self._criar_missoes()
        self._criar_informacoes(missoes, npcs)
        self._criar_sessoes()

        self.stdout.write(self.style.SUCCESS("\n=== Pronto! Banco populado com sucesso. ==="))
        self.stdout.write("Acesse http://127.0.0.1:8000/ para ver os dados.")

    # ------------------------------------------------------------------ #
    #  Personagem                                                          #
    # ------------------------------------------------------------------ #
    def _criar_personagem(self):
        personagem, created = Personagem.objects.get_or_create(
            nome="Rollo Stoneblood",
            defaults={
                "raca": "Golias",
                "classe": "Bárbaro",
                "nivel": 5,
                "forca": 20,
                "destreza": 14,
                "constituicao": 14,
                "inteligencia": 12,
                "sabedoria": 13,
                "carisma": 12,
                "bonus_proficiencia": 3,
                "ca": 16,
                "pv_maximo": 55,
                "pv_atual": 55,
                "pv_temporario": 0,
                "deslocamento": 12,
                "background": BACKGROUND_ROLLO,
                "moedas_pc": 0,
                "moedas_pp": 7,
                "moedas_pe": 0,
                "moedas_po": 48,
                "moedas_pl": 0,
            },
        )
        label = "criado" if created else "já existia"
        self.stdout.write(f"  Personagem '{personagem.nome}' — {label}")
        return personagem

    # ------------------------------------------------------------------ #
    #  Proficiências                                                       #
    # ------------------------------------------------------------------ #
    def _configurar_proficiencias(self, personagem):
        pericias_prof = ["atletismo", "percepcao", "intimidacao"]
        salvaguardas_prof = ["forca", "constituicao"]

        updated_p = Pericia.objects.filter(
            personagem=personagem, identificador__in=pericias_prof
        ).update(proficiente=True)

        updated_s = Salvaguarda.objects.filter(
            personagem=personagem, identificador__in=salvaguardas_prof
        ).update(proficiente=True)

        self.stdout.write(
            f"  Proficiências: {updated_p} perícias, {updated_s} salvaguardas marcadas"
        )

    # ------------------------------------------------------------------ #
    #  Recursos de Combate                                                 #
    # ------------------------------------------------------------------ #
    def _criar_recursos(self, personagem):
        recursos = [
            {
                "nome": "Fúria",
                "descricao": (
                    "Ação bônus para ativar. Enquanto ativa: resistência a Bludgeoning/Piercing/Slashing, "
                    "+2 dano em ataques corpo a corpo com Força, vantagem em testes e saves de Força. "
                    "Dura até 10 minutos. ATENÇÃO: recupera TODOS os usos no descanso longo; "
                    "recupera apenas 1 uso por descanso curto (ajuste manualmente se necessário)."
                ),
                "usos_totais": 3,
                "usos_restantes": 3,
                "recuperacao": "curto",
                "checklist_turno": (
                    "[ ] Ativar Fúria (Ação Bônus) — ganhar 5 PV temporários\n"
                    "[ ] TODO TURNO: dar 2d6 PV temporários para aliado a 3m\n"
                    "[ ] Atacar (+7 / 1d8+7)\n"
                    "[ ] Usar Reckless Attack se precisar garantir acerto\n"
                    "[ ] Manter Fúria ativa (precisa atacar ou receber dano)"
                ),
            },
            {
                "nome": "Stone's Endurance",
                "descricao": (
                    "Reação. Reduz dano em 1d12 + 2 (CON). "
                    "Usar quando: tomar dano alto, crítico, ou antes de cair."
                ),
                "usos_totais": 2,
                "usos_restantes": 2,
                "recuperacao": "longo",
                "checklist_turno": "",
            },
        ]

        for r in recursos:
            nome = r.pop("nome")
            obj, created = RecursoDeCombate.objects.get_or_create(
                personagem=personagem,
                nome=nome,
                defaults=r,
            )
            label = "criado" if created else "já existia"
            self.stdout.write(f"  Recurso '{nome}' — {label}")

    # ------------------------------------------------------------------ #
    #  Inventário                                                          #
    # ------------------------------------------------------------------ #
    def _criar_inventario(self, personagem):
        itens = [
            # Equipados
            {
                "nome": "Machado de Batalha",
                "tipo": "equipado",
                "quantidade": 1,
                "atributos_efeito": "1d8 + FOR (Versátil 1d10). Propriedade Derrubar: se acertar, criatura faz save CON CD=8+prof+FOR ou cai Caído.",
                "lore": "",
            },
            {
                "nome": "Escudo",
                "tipo": "equipado",
                "quantidade": 1,
                "atributos_efeito": "+2 AC",
                "lore": "",
            },
            # Mochila
            {
                "nome": "Ração",
                "tipo": "mochila",
                "quantidade": 5,
                "atributos_efeito": "",
                "lore": "",
            },
            {
                "nome": "Kit de Jogos (Dados)",
                "tipo": "mochila",
                "quantidade": 1,
                "atributos_efeito": "Proficiência em ferramentas. Útil para ganhar dinheiro, interações sociais, contatos, distrair NPCs.",
                "lore": "",
            },
            {
                "nome": "Corda",
                "tipo": "mochila",
                "quantidade": 1,
                "atributos_efeito": "",
                "lore": "",
            },
            {
                "nome": "Cantil",
                "tipo": "mochila",
                "quantidade": 1,
                "atributos_efeito": "Cheio",
                "lore": "",
            },
        ]

        for item_data in itens:
            nome = item_data["nome"]
            obj, created = ItemInventario.objects.get_or_create(
                personagem=personagem,
                nome=nome,
                defaults=item_data,
            )
            label = "criado" if created else "já existia"
            self.stdout.write(f"  Item '{nome}' — {label}")

    # ------------------------------------------------------------------ #
    #  Locais                                                              #
    # ------------------------------------------------------------------ #
    def _criar_locais(self):
        locais_data = [
            {
                "nome": "Ravenshire",
                "tipo": "cidade",
                "descricao": "Cidade base do grupo. Ponto de criação do Escudo de Belmora. Administrada por Lorde Lirion Lannis.",
                "status": "Base atual do grupo",
            },
            {
                "nome": "Vila de Enzam",
                "tipo": "vila",
                "descricao": "Vila afetada pelo incêndio. Local da missão do Espírito Mascarado (Yokai).",
                "status": "Em reconstrução",
            },
            {
                "nome": "Aella",
                "tipo": "cidade",
                "descricao": "Cidade a 3 dias de viagem a pé. Local do contratante da missão Filha Desaparecida.",
                "status": "Ainda não visitada",
            },
            {
                "nome": "Região do Solstício Vermelho (Sul)",
                "tipo": "regiao",
                "descricao": "Região ao sul, a 10 dias de viagem. Local do evento Solstício Vermelho. Nome ainda não definido pelo Mestre.",
                "status": "Pendente",
            },
            {
                "nome": "Helindor",
                "tipo": "vila",
                "descricao": (
                    "Ilha com clima anormalmente frio, base da Igreja da Lua. "
                    "Devastada após o grupo despertar gigantes congelados nas ruínas sob o cemitério. "
                    "Abriga a cripta de Bharomil e ruínas antigas com inscrição em língua de gigantes. "
                    "Elyra (elfa) mencionou raízes gigantescas pulsantes sob a montanha."
                ),
                "status": "Devastada — gigantes soltos",
            },
            {
                "nome": "Kilmena",
                "tipo": "vila",
                "descricao": "Vilarejo portuário. Ponto de embarque para Helindor.",
                "status": "Visitada",
            },
            {
                "nome": "Base do Escudo de Belmora",
                "tipo": "base",
                "descricao": "Terras concedidas por Lirion Lannis. Possui bandeira oficial, carroça e dois cavalos. Lago próximo foi congelado pelo cubo de Lyrion.",
                "status": "Ativa — sede da guilda",
            },
            {
                "nome": "Novigrad",
                "tipo": "cidade",
                "descricao": "Capital de Belmora. Território de Aelar (filho de Sylvaris). Possui mestre ferreiro capaz de restaurar aço valyriano.",
                "status": "Ainda não visitada",
            },
            {
                "nome": "Floresta de Valen",
                "tipo": "regiao",
                "descricao": (
                    "Mais antiga que o império. Lar de Tharn, o Casco Antigo. "
                    "A floresta tem consciência própria: javalis com musgo e flores, árvores humanoides, "
                    "cervo branco sem magia. Entidades que chegam com más intenções são combatidas pela floresta."
                ),
                "status": "Visitada — Tharn encontrado",
            },
            {
                "nome": "Reino Umbral",
                "tipo": "regiao",
                "descricao": "Lar dos Drows. Controlado por Vysania, irmã mais nova de Sylvaris.",
                "status": "Ainda não visitado",
            },
            {
                "nome": "Valcarys",
                "tipo": "regiao",
                "descricao": "Terra natal de Elyndor, irmão mais velho de Sylvaris. Elyndor nunca concordou com a conquista do continente.",
                "status": "Ainda não visitado",
            },
        ]

        locais = {}
        for data in locais_data:
            nome = data["nome"]
            obj, created = Local.objects.get_or_create(nome=nome, defaults=data)
            label = "criado" if created else "já existia"
            self.stdout.write(f"  Local '{nome}' — {label}")
            locais[nome] = obj

        return locais

    # ------------------------------------------------------------------ #
    #  NPCs                                                                #
    # ------------------------------------------------------------------ #
    def _criar_npcs(self, locais):
        npcs_data = [
            # Ravenshire
            {
                "nome": "Lirion Lannis",
                "local_nome": "Ravenshire",
                "descricao": (
                    "Lorde de Ravenshire. Antigo aliado de Eren (herói histórico). Viveu durante a ascensão e queda "
                    "de Sylvaris. Passou anos como conselheiro oculto antes de assumir a liderança para impedir Aelar. "
                    "Cedeu terras ao Escudo de Belmora. Pediu que o grupo encontrasse os Custódios e levasse o cubo a Tharn."
                ),
                "relacao_grupo": "aliado",
            },
            {
                "nome": "Madalena",
                "local_nome": "Ravenshire",
                "descricao": "Dona da taverna onde o grupo descansa ao retornar à cidade. Mãe de Maria.",
                "relacao_grupo": "aliado",
            },
            {
                "nome": "Ferb",
                "local_nome": "Ravenshire",
                "descricao": "Armadilheiro. Avalia e vende itens incomuns da missão. Cobra comissão sobre vendas futuras.",
                "relacao_grupo": "aliado",
            },
            {
                "nome": "Fyllas",
                "local_nome": "Ravenshire",
                "descricao": "Ferreiro especializado em armas e armaduras. Recomenda o armadilheiro para itens incomuns.",
                "relacao_grupo": "neutro",
            },
            {
                "nome": "Thomas",
                "local_nome": "Ravenshire",
                "descricao": "Intermediário da missão Filha Desaparecida. Informou que o contratante está em Aella.",
                "relacao_grupo": "neutro",
            },
            {
                "nome": "Almir",
                "local_nome": "Ravenshire",
                "descricao": "Escriba de Ravenshire.",
                "relacao_grupo": "neutro",
            },
            {
                "nome": "João",
                "local_nome": "Ravenshire",
                "descricao": "Atendente da guilda. Noivo de Maria (filha de Madalena). Informou que a loja de poções foi abandonada.",
                "relacao_grupo": "neutro",
            },
            {
                "nome": "Maria",
                "local_nome": "Ravenshire",
                "descricao": "Filha de Madalena. Vai se casar com João.",
                "relacao_grupo": "neutro",
            },
            # Vila de Enzam
            {
                "nome": "Harkan",
                "local_nome": "Vila de Enzam",
                "descricao": (
                    "Padre de Enzam. Responsável pela missão do Espírito Mascarado. Explicou o incêndio, "
                    "o Yokai e os efeitos sobre os moradores. Ajudou o grupo a realizar o exorcismo dos halflings."
                ),
                "relacao_grupo": "aliado",
            },
            {
                "nome": "Reika",
                "local_nome": "Helindor",
                "descricao": (
                    "Ligada à Igreja de Tyr. Desconfia da Igreja da Lua — acredita que provocaram o incêndio que "
                    "matou seu marido. Forneceu comida segura ao grupo em Helindor (sopa de flores medicinais). "
                    "Lutou sozinha contra demônios. Resgatada pelo grupo na fuga dos gigantes."
                ),
                "relacao_grupo": "aliado",
            },
            {
                "nome": "Amara",
                "local_nome": "Vila de Enzam",
                "descricao": "Mulher afetada pelo Yokai. Não via a entidade como inimiga — acreditava que estava sendo ajudada.",
                "relacao_grupo": "neutro",
            },
            {
                "nome": "Harkin",
                "local_nome": "Vila de Enzam",
                "descricao": "Halfling, morador de Enzam. Afetado pelas sombras do Yokai. Libertado pelo exorcismo do grupo.",
                "relacao_grupo": "neutro",
            },
            {
                "nome": "Durgan",
                "local_nome": "Vila de Enzam",
                "descricao": "Halfling, parceiro de Harkin. Também afetado pelas sombras. Perdeu um filho no incêndio.",
                "relacao_grupo": "neutro",
            },
            # Helindor
            {
                "nome": "Irmão Liam",
                "local_nome": "Helindor",
                "descricao": (
                    "Membro luxuosamente vestido da Igreja da Lua. Afirma ter sido salvo da morte pela 'Princesa' "
                    "após ter sofrido uma condição incurável. Recebeu o grupo de forma calorosa."
                ),
                "relacao_grupo": "suspeito",
            },
            {
                "nome": "Glint",
                "local_nome": "Helindor",
                "descricao": (
                    "Curandeiro responsável pela 'Redenção'. Realiza curas reais e milagrosas. "
                    "Durante o ritual, palavras em Abyssal saíram de sua boca e abriram um portal demoníaco — "
                    "ele mesmo estava assustado e confuso, sem entender o que aconteceu. Possivelmente controlado."
                ),
                "relacao_grupo": "suspeito",
            },
            # Floresta de Valen
            {
                "nome": "Tharn, o Casco Antigo",
                "local_nome": "Floresta de Valen",
                "descricao": (
                    "Velho amigo de Lirion. Vive no interior de uma árvore gigante na Floresta de Valen. "
                    "Removeu o selo da carta de Elyra/Bharomil. Explicou sobre artefatos com vontade própria. "
                    "Disse que para descobrir a finalidade do cubo o grupo precisaria ir mais fundo em Helindor."
                ),
                "relacao_grupo": "aliado",
            },
            # Figuras históricas / sem local fixo
            {
                "nome": "Sylvaris",
                "local_nome": None,
                "descricao": (
                    "Antigo imperador que unificou todo o continente. Morreu sem deixar sucessores claros, "
                    "fragmentando o império. Roubou o Ovo de Dragão de Lyssandra. Realizou uma pesquisa "
                    "chamada 'O Núcleo' que todos os herdeiros buscam."
                ),
                "relacao_grupo": "inimigo",
            },
            {
                "nome": "Eren",
                "local_nome": None,
                "descricao": "Um dos antigos heróis. Aliado histórico de Lirion Lannis.",
                "relacao_grupo": "aliado",
            },
            {
                "nome": "Aelar",
                "local_nome": "Novigrad",
                "descricao": (
                    "Primeiro filho de Sylvaris. General da guerra de conquista. "
                    "Controla Novigrad, que considera a verdadeira capital do antigo império."
                ),
                "relacao_grupo": "inimigo",
            },
            {
                "nome": "Seris",
                "local_nome": None,
                "descricao": (
                    "Filha mais nova de Sylvaris. Diferente do irmão Aelar, busca conhecimento. "
                    "Disputa as terras centrais do antigo império com Aelar."
                ),
                "relacao_grupo": "neutro",
            },
            {
                "nome": "Vysania",
                "local_nome": "Reino Umbral",
                "descricao": "Irmã mais nova de Sylvaris. Controla o Reino Umbral, lar dos Drows.",
                "relacao_grupo": "suspeito",
            },
            {
                "nome": "Elyndor",
                "local_nome": "Valcarys",
                "descricao": (
                    "Irmão mais velho de Sylvaris. Nunca concordou com a conquista do continente. "
                    "Após a morte do irmão, retornou a Valcarys, sua terra natal."
                ),
                "relacao_grupo": "neutro",
            },
            {
                "nome": "Contratante (Filha Desaparecida)",
                "local_nome": "Aella",
                "descricao": "Contratante da missão Filha Desaparecida. Está em Aella. Identidade ainda desconhecida.",
                "relacao_grupo": "desconhecido",
            },
        ]

        npcs = {}
        for data in npcs_data:
            local_nome = data.pop("local_nome")
            local = locais.get(local_nome) if local_nome else None
            nome = data["nome"]
            obj, created = NPC.objects.get_or_create(
                nome=nome,
                defaults={**data, "local": local},
            )
            label = "criado" if created else "já existia"
            self.stdout.write(f"  NPC '{nome}' — {label}")
            npcs[nome] = obj

        return npcs

    # ------------------------------------------------------------------ #
    #  Missões                                                             #
    # ------------------------------------------------------------------ #
    def _criar_missoes(self):
        missoes_data = [
            # Ativas
            {
                "titulo": "Encontrar Tharn, o Casco Antigo",
                "descricao": (
                    "Ir até a Floresta de Valen e encontrar Tharn. "
                    "Objetivos: investigar a carta misteriosa encontrada na cripta de Bharomil e descobrir "
                    "a finalidade do cubo mágico que o grupo pegou em Helindor."
                ),
                "status": "ativa",
                "resultado": "",
            },
            {
                "titulo": "Encontrar os Custódios",
                "descricao": (
                    "Localizar os Custódios — guerreiros de elite jurados a Sylvaris, libertos após sua queda. "
                    "Último registro: extremo sul, 42 anos atrás. Eram 12; número atual desconhecido. "
                    "Objetivo: impedir que qualquer das quatro forças herdeiras use esse poder. "
                    "ATENÇÃO: não confrontar diretamente — são lendas."
                ),
                "status": "ativa",
                "resultado": "",
            },
            {
                "titulo": "Ovo de Dragão de Lyssandra",
                "descricao": (
                    "Investigar e recuperar um Ovo de Dragão roubado por Sylvaris. "
                    "Lyssandra veio de outro continente em busca deste artefato. "
                    "Lirion prometeu investigar mais informações sobre o ovo."
                ),
                "status": "ativa",
                "resultado": "",
            },
            {
                "titulo": "Filha Desaparecida",
                "descricao": (
                    "Investigar o desaparecimento de uma filha. O contratante está em Aella (3 dias de viagem). "
                    "Thomas (Ravenshire) é o intermediário."
                ),
                "status": "ativa",
                "resultado": "",
            },
            {
                "titulo": "Solstício Vermelho",
                "descricao": (
                    "Missão pendente. Relacionada a um evento no sul do continente (10 dias de viagem). "
                    "Nome da cidade de destino ainda não definido pelo Mestre."
                ),
                "status": "ativa",
                "resultado": "",
            },
            # Concluídas
            {
                "titulo": "Espírito Mascarado",
                "descricao": (
                    "Investigar as pessoas agindo de forma estranha na Vila de Enzam após um incêndio. "
                    "Um Yokai chamado 'Coletor de Pesares' estava removendo a negatividade das pessoas."
                ),
                "status": "concluida",
                "resultado": (
                    "Yokai derrotado em segundo confronto. Vila estabilizada. "
                    "Halflings Harkin e Durgan libertados via exorcismo com ajuda do Padre Harkan. "
                    "Recompensa recebida."
                ),
            },
            {
                "titulo": "Mistério da Redenção de Helindor",
                "descricao": (
                    "Investigar o evento 'Redenção' na Ilha de Helindor e o que a Igreja da Lua estava fazendo. "
                    "Comida distribuída continha magia; Órun detectou possível controle mental."
                ),
                "status": "concluida",
                "resultado": (
                    "Manipulação descoberta. Glint (curandeiro) parecia controlado — invocou demônios durante o ritual "
                    "sem intenção aparente. Demônios derrotados, prisioneiros da cripta libertados. "
                    "O grupo acidentalmente despertou gigantes congelados ao pegar o cubo. Helindor devastada. "
                    "Resultado: vitória parcial com consequências graves."
                ),
            },
        ]

        missoes = {}
        for data in missoes_data:
            titulo = data["titulo"]
            obj, created = Missao.objects.get_or_create(titulo=titulo, defaults=data)
            label = "criada" if created else "já existia"
            self.stdout.write(f"  Missão '{titulo}' — {label}")
            missoes[titulo] = obj

        return missoes

    # ------------------------------------------------------------------ #
    #  Informações Importantes                                             #
    # ------------------------------------------------------------------ #
    def _criar_informacoes(self, missoes, npcs):
        # (texto, missao_titulo_ou_None, npc_nome_ou_None)
        infos = [
            ("Helindor possui clima anormalmente frio apesar de estar numa região quente.",
             "Mistério da Redenção de Helindor", None),
            ("A comida distribuída pela Igreja da Lua em Helindor contém magia.",
             "Mistério da Redenção de Helindor", "Irmão Liam"),
            ("Órun detectou possível controle mental afetando as pessoas em Helindor.",
             "Mistério da Redenção de Helindor", None),
            ("Reika acredita que a Igreja da Lua queimou a igreja de Tyr propositalmente.",
             "Mistério da Redenção de Helindor", "Reika"),
            ("Flores medicinais dos arredores de Helindor estão desaparecendo.",
             "Mistério da Redenção de Helindor", None),
            ("Glint consegue realizar curas reais e milagrosas.",
             "Mistério da Redenção de Helindor", "Glint"),
            ("Durante a Redenção, Glint proferiu palavras em Abyssal e demônios foram invocados.",
             "Mistério da Redenção de Helindor", "Glint"),
            ("Glint parecia apavorado após a invocação, como se não tivesse controle total da situação.",
             "Mistério da Redenção de Helindor", "Glint"),
            ("Rollo segurou o demônio principal durante o combate da Redenção enquanto o grupo lidava com os menores.",
             "Mistério da Redenção de Helindor", None),
        ]

        for texto, missao_titulo, npc_nome in infos:
            missao = missoes.get(missao_titulo) if missao_titulo else None
            npc = npcs.get(npc_nome) if npc_nome else None
            obj, created = InformacaoImportante.objects.get_or_create(
                texto=texto,
                defaults={"missao": missao, "npc": npc},
            )
            label = "criada" if created else "já existia"
            self.stdout.write(f"  Info '{texto[:60]}…' — {label}")

    # ------------------------------------------------------------------ #
    #  Resumos de Sessão                                                   #
    # ------------------------------------------------------------------ #
    def _criar_sessoes(self):
        for numero, titulo, resumo in SESSOES:
            obj, created = ResumoSessao.objects.get_or_create(
                numero=numero,
                defaults={"titulo": titulo, "resumo": resumo},
            )
            label = "criado" if created else "já existia"
            self.stdout.write(f"  Sessão {numero} '{titulo}' — {label}")
