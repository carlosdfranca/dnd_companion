# Migração escrita à mão (não via `makemigrations` interativo) para garantir
# que o RenameModel/RenameField sejam preservados — ver nota em regras.py e
# no relatório de investigação: o prompt "Did you rename X to Y?" do
# makemigrations, se respondido incorretamente ou rodado sem TTY, gera
# DeleteModel+CreateModel e apaga os registros existentes.
#
# Escopo: renomeia ItemInventario -> Equipamento e acrescenta os campos do
# sistema de efeitos estruturados (slot, sintonização, dano de arma, CA de
# armadura) + o model EfeitoItem. Não adiciona a UniqueConstraint de slot
# único ainda (fica para 0013, depois que os dados dos 8 itens existentes
# estiverem migrados) e não remove o campo `tipo` (fica vestigial até uma
# migração futura). Também remove o model Ataque (ver models.py) — a única
# linha real que ele tinha (Machado de Batalha) foi preservada num backup
# lógico antes desta migração e seu dado equivalente é recriado em
# Equipamento na migração seguinte (0012).

import django.db.models.deletion
from django.db import migrations, models


def none_forward(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('campanha', '0010_personagem_bonus_dano_furia_ataque'),
    ]

    operations = [
        # ── Personagem: CA vira override + estilo de CA sem armadura ───────
        migrations.RenameField(
            model_name='personagem', old_name='ca', new_name='ca_override',
        ),
        migrations.AlterField(
            model_name='personagem',
            name='ca_override',
            field=models.PositiveSmallIntegerField(
                blank=True, null=True,
                help_text='Deixe em branco para calcular automaticamente a partir do '
                          'equipamento. Preencha só quando o motor não conseguir modelar algo.',
                verbose_name='CA (override manual)',
            ),
        ),
        migrations.AddField(
            model_name='personagem',
            name='estilo_ca',
            field=models.CharField(
                choices=[
                    ('desarmado', 'Sem armadura (10 + DES)'),
                    ('barbaro', 'Defesa sem Armadura — Bárbaro (+CON)'),
                    ('monge', 'Defesa sem Armadura — Monge (+SAB)'),
                    ('draconico', 'Resiliência Dracônica (13 + DES)'),
                ],
                default='desarmado', max_length=12,
                help_text='Usado como base da CA quando nenhuma armadura corporal estiver equipada.',
                verbose_name='Estilo de CA sem armadura',
            ),
        ),

        # ── ItemInventario -> Equipamento ───────────────────────────────────
        migrations.RenameModel(old_name='ItemInventario', new_name='Equipamento'),
        migrations.AlterModelOptions(
            name='equipamento',
            options={
                'ordering': ['slot', 'ordem', 'nome'],
                'verbose_name': 'Equipamento',
                'verbose_name_plural': 'Equipamentos',
            },
        ),
        migrations.RenameField(
            model_name='equipamento', old_name='atributos_efeito', new_name='atributos_efeito_legado',
        ),
        migrations.AlterField(
            model_name='equipamento',
            name='atributos_efeito_legado',
            field=models.TextField(
                blank=True, editable=False,
                help_text="Preservado do antigo campo 'Atributos / Efeito' na migração para efeitos estruturados.",
                verbose_name='Texto original (legado)',
            ),
        ),
        migrations.AlterField(
            model_name='equipamento',
            name='tipo',
            field=models.CharField(
                choices=[('equipado', 'Equipado'), ('mochila', 'Mochila')],
                default='mochila', max_length=10,
                help_text='Campo legado — a localização real é decidida pelo slot.',
                verbose_name='Localização (legado)',
            ),
        ),
        migrations.AlterField(
            model_name='equipamento',
            name='requer_sintonizacao',
            field=models.BooleanField(
                default=False,
                help_text="Propriedade do item — junto com 'Sintonizado' decide se os efeitos contam.",
                verbose_name='Requer Sintonização',
            ),
        ),

        # Campos novos herdados de ItemBase (personagem/nome/quantidade/lore já
        # existiam e não mudam de definição).
        migrations.AddField(
            model_name='equipamento',
            name='raridade',
            field=models.CharField(
                choices=[
                    ('comum', 'Comum'), ('incomum', 'Incomum'), ('raro', 'Raro'),
                    ('muito_raro', 'Muito Raro'), ('lendario', 'Lendário'),
                ],
                default='comum', max_length=12, verbose_name='Raridade',
            ),
        ),
        migrations.AddField(
            model_name='equipamento',
            name='peso',
            field=models.DecimalField(
                decimal_places=2, default=0, max_digits=6,
                help_text='Usado para o total de carga (capacidade = Força × 7,5 kg).',
                verbose_name='Peso (kg, por unidade)',
            ),
        ),

        # Campos novos de slot/empunhadura/sintonização/dano/armadura.
        migrations.AddField(
            model_name='equipamento',
            name='categoria',
            field=models.CharField(
                choices=[
                    ('arma', 'Arma'), ('armadura', 'Armadura'), ('escudo', 'Escudo'),
                    ('acessorio', 'Acessório'), ('municao', 'Munição'), ('diverso', 'Diverso'),
                ],
                default='diverso', max_length=12, verbose_name='Categoria',
            ),
        ),
        migrations.AddField(
            model_name='equipamento',
            name='slot',
            field=models.CharField(
                blank=True, default='', max_length=20,
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
        migrations.AddField(
            model_name='equipamento',
            name='slot_padrao',
            field=models.CharField(
                blank=True, default='', max_length=20,
                choices=[
                    ('mao_principal', 'Mão Principal'), ('mao_secundaria', 'Mão Secundária'),
                    ('armadura_corporal', 'Armadura Corporal'), ('capa', 'Capa / Manto'),
                    ('cabeca', 'Cabeça'), ('colar', 'Colar / Amuleto'), ('cinto', 'Cinto'),
                    ('anel_1', 'Anel 1'), ('anel_2', 'Anel 2'), ('luvas', 'Luvas'),
                    ('botas', 'Botas'), ('municao', 'Munição'),
                ],
                verbose_name='Slot padrão ao equipar',
            ),
        ),
        migrations.AddField(
            model_name='equipamento',
            name='empunhadura',
            field=models.CharField(
                choices=[('uma', 'Uma Mão'), ('duas', 'Duas Mãos')],
                default='uma', max_length=4, verbose_name='Empunhadura',
            ),
        ),
        migrations.AddField(
            model_name='equipamento',
            name='duas_maos',
            field=models.BooleanField(
                default=False, help_text='Arma inerentemente de duas mãos (não versátil).',
                verbose_name='Sempre duas mãos',
            ),
        ),
        migrations.AddField(
            model_name='equipamento',
            name='versatil',
            field=models.BooleanField(
                default=False, help_text='Muda o dado de dano quando empunhada com duas mãos.',
                verbose_name='Versátil',
            ),
        ),
        migrations.AddField(
            model_name='equipamento',
            name='sintonizado',
            field=models.BooleanField(
                default=False,
                help_text="Estado do personagem. Só é relevante se 'Requer Sintonização' for verdadeiro.",
                verbose_name='Sintonizado',
            ),
        ),
        migrations.AddField(
            model_name='equipamento',
            name='dano_qtd_dados',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='Qtd. de Dados de Dano'),
        ),
        migrations.AddField(
            model_name='equipamento',
            name='dano_faces',
            field=models.PositiveSmallIntegerField(
                choices=[(4, 'd4'), (6, 'd6'), (8, 'd8'), (10, 'd10'), (12, 'd12'), (20, 'd20')],
                default=8, verbose_name='Dado de Dano',
            ),
        ),
        migrations.AddField(
            model_name='equipamento',
            name='dano_faces_versatil',
            field=models.PositiveSmallIntegerField(
                blank=True, null=True,
                choices=[(4, 'd4'), (6, 'd6'), (8, 'd8'), (10, 'd10'), (12, 'd12'), (20, 'd20')],
                verbose_name='Dado de Dano (versátil, 2 mãos)',
            ),
        ),
        migrations.AddField(
            model_name='equipamento',
            name='tipo_dano',
            field=models.CharField(
                blank=True, max_length=15,
                choices=[
                    ('cortante', 'Cortante'), ('perfurante', 'Perfurante'),
                    ('concussao', 'Concussão'), ('acido', 'Ácido'), ('frio', 'Frio'),
                    ('fogo', 'Fogo'), ('eletrico', 'Elétrico'), ('necrotico', 'Necrótico'),
                    ('psiquico', 'Psíquico'), ('radiante', 'Radiante'),
                    ('trovejante', 'Trovejante'), ('veneno', 'Veneno'),
                    ('energia', 'Energia (Força)'),
                ],
                verbose_name='Tipo de Dano',
            ),
        ),
        migrations.AddField(
            model_name='equipamento',
            name='atributo_ataque',
            field=models.CharField(
                choices=[
                    ('forca', 'Força'), ('destreza', 'Destreza'), ('constituicao', 'Constituição'),
                    ('inteligencia', 'Inteligência'), ('sabedoria', 'Sabedoria'), ('carisma', 'Carisma'),
                ],
                default='forca', max_length=12, verbose_name='Atributo de Ataque',
            ),
        ),
        migrations.AddField(
            model_name='equipamento',
            name='proficiente',
            field=models.BooleanField(default=True, verbose_name='Proficiente'),
        ),
        migrations.AddField(
            model_name='equipamento',
            name='alcance',
            field=models.CharField(blank=True, max_length=40, verbose_name='Alcance'),
        ),
        migrations.AddField(
            model_name='equipamento',
            name='categoria_armadura',
            field=models.CharField(
                blank=True, max_length=10,
                choices=[
                    ('leve', 'Armadura Leve'), ('media', 'Armadura Média'), ('pesada', 'Armadura Pesada'),
                ],
                help_text='Preencha só se este item for uma armadura VESTIDA (não escudo).',
                verbose_name='Categoria de Armadura',
            ),
        ),
        migrations.AddField(
            model_name='equipamento',
            name='ca_base_armadura',
            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='CA base da armadura'),
        ),
        migrations.AddField(
            model_name='equipamento',
            name='propriedades_texto',
            field=models.TextField(
                blank=True,
                help_text='Regra narrativa que o motor não automatiza (ex.: Derrubar).',
                verbose_name='Propriedades (texto livre)',
            ),
        ),
        migrations.AddField(
            model_name='equipamento',
            name='ordem',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='Ordem'),
        ),

        # ── EfeitoItem ───────────────────────────────────────────────────────
        migrations.CreateModel(
            name='EfeitoItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('categoria', models.CharField(
                    choices=[
                        ('numerico', 'Bônus numérico'), ('palavra_chave', 'Palavra-chave'),
                        ('informativo', 'Informativo'),
                    ],
                    default='numerico', max_length=15, verbose_name='Categoria',
                )),
                ('alvo', models.CharField(
                    blank=True, max_length=30,
                    choices=[
                        ('ca', 'Classe de Armadura'), ('salvaguardas_todas', 'Todas as Salvaguardas'),
                        ('save_forca', 'Salvaguarda de Força'), ('save_destreza', 'Salvaguarda de Destreza'),
                        ('save_constituicao', 'Salvaguarda de Constituição'),
                        ('save_inteligencia', 'Salvaguarda de Inteligência'),
                        ('save_sabedoria', 'Salvaguarda de Sabedoria'), ('save_carisma', 'Salvaguarda de Carisma'),
                        ('ataque', 'Jogadas de Ataque'), ('dano', 'Jogadas de Dano'),
                        ('iniciativa', 'Iniciativa'), ('pericias_todas', 'Todos os testes de perícia'),
                    ],
                    verbose_name='Alvo',
                )),
                ('valor', models.SmallIntegerField(default=0, verbose_name='Valor')),
                ('tipo_bonus', models.CharField(
                    blank=True, max_length=20,
                    choices=[
                        ('armadura', 'Armadura'), ('escudo', 'Escudo'), ('deflexao', 'Deflexão'),
                        ('natural', 'Armadura Natural'), ('aprimoramento', 'Aprimoramento'),
                    ],
                    help_text='Bônus do MESMO tipo não acumulam (vale o maior). Deixe em branco '
                              'para um bônus sem tipo, que sempre acumula.',
                    verbose_name='Tipo de Bônus',
                )),
                ('palavra_chave', models.CharField(
                    blank=True, max_length=25,
                    choices=[
                        ('resistencia', 'Resistência a dano'), ('imunidade', 'Imunidade a dano'),
                        ('vulnerabilidade', 'Vulnerabilidade a dano'), ('vantagem', 'Vantagem'),
                        ('desvantagem', 'Desvantagem'), ('imunidade_condicao', 'Imunidade a condição'),
                        ('visao_no_escuro', 'Visão no escuro'),
                    ],
                    verbose_name='Palavra-chave',
                )),
                ('tipo_dano', models.CharField(
                    blank=True, max_length=15,
                    choices=[
                        ('cortante', 'Cortante'), ('perfurante', 'Perfurante'), ('concussao', 'Concussão'),
                        ('acido', 'Ácido'), ('frio', 'Frio'), ('fogo', 'Fogo'), ('eletrico', 'Elétrico'),
                        ('necrotico', 'Necrótico'), ('psiquico', 'Psíquico'), ('radiante', 'Radiante'),
                        ('trovejante', 'Trovejante'), ('veneno', 'Veneno'), ('energia', 'Energia (Força)'),
                    ],
                    verbose_name='Tipo de Dano',
                )),
                ('condicao', models.CharField(
                    blank=True, max_length=120,
                    help_text="Se preenchido, o efeito é SITUACIONAL: aparece na ficha, mas NÃO é "
                              "somado automaticamente. Ex.: 'apenas contra mortos-vivos'.",
                    verbose_name='Condição',
                )),
                ('descricao', models.CharField(blank=True, max_length=250, verbose_name='Descrição')),
                ('ordem', models.PositiveSmallIntegerField(default=0, verbose_name='Ordem')),
                ('equipamento', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name='efeitos', to='campanha.equipamento',
                )),
            ],
            options={
                'verbose_name': 'Efeito de Item',
                'verbose_name_plural': 'Efeitos de Item',
                'ordering': ['ordem', 'id'],
            },
        ),

        # ── Remove o model Ataque ───────────────────────────────────────────
        # A única linha real (Machado de Batalha) está preservada em backup
        # lógico; seu dado equivalente é recriado em Equipamento na 0012.
        migrations.DeleteModel(name='Ataque'),
    ]
