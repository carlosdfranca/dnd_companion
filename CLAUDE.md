# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A personal Django web app for tracking a single D&D 5e campaign/character (character sheet, combat tracker, inventory, NPCs, locations, quests, session logs). Single-player use today — UI and copy are in Portuguese (pt-br).

## Commands

Run from the repo root (`dnd_companion/` — the folder containing `manage.py`).

```
python manage.py runserver          # dev server
python manage.py migrate            # apply migrations
python manage.py makemigrations campanha
python manage.py test campanha      # run tests (currently no tests written)
python manage.py test campanha.tests.SomeTestCase.test_method  # single test
python manage.py createsuperuser
python manage.py populate_belmora   # idempotent seed of the "Belmora" campaign fixture data
```

No package.json/build step — pure Django, server-rendered templates, SQLite (`db.sqlite3`).

## Architecture

Single Django project (`dnd_companion/`) with a single app (`campanha/`) that holds all models, views, forms, templates, and URLs.

- **"Current character" resolution**: `campanha/utils.py:get_current_character()` is the one place that decides which `Personagem` is active (currently just returns the first row; the field/session lookup path is a stub for future multi-character support). All views that need the active character go through this function rather than querying `Personagem` directly.
- **D&D rules vs. per-character data split**: fixed 5e rule tables (the 18 perícias, 6 salvaguardas, and which ability score governs each) live as code constants in `campanha/constants.py`, keyed by a stable `identificador` string. The DB only stores what's personal to the character (the `proficiente` boolean via `Pericia`/`Salvaguarda` models, FK'd to `Personagem`). Labels, governing attribute, and display order are looked up from `constants.py` at read time — never duplicate rule data into migrations.
- **Auto-seeding via signals**: `campanha/signals.py` listens for `post_save` on `Personagem` creation and creates all 18 `Pericia` + 6 `Salvaguarda` rows via `get_or_create` (idempotent). Wired up in `CampanhaConfig.ready()` (`campanha/apps.py`) — don't forget a new `Personagem` still needs these rows if created outside the normal flow (e.g. fixtures/scripts must call the same seeding or rely on the signal firing).
- **Ability modifiers are always computed, never stored**: `Personagem.modificador(attr)` / the `mod_forca` etc. properties apply the 5e formula (`floor((score-10)/2)`) on read. Same pattern for perícia/salvaguarda `modificador_total` (attribute mod + proficiency bonus if proficient).
- **Markdown rendering with sanitization**: `campanha/markup.py:render_md()` converts Markdown to HTML and passes it through a hand-rolled allowlist `HTMLParser` sanitizer (`_ALLOWED_TAGS`/`_ALLOWED_ATTRS`, URL scheme check) before use — this is the only sanitization layer, so any new place that renders user-authored free text as HTML should go through this function (exposed as the `md` template filter in `campanha/templatetags/bel_filters.py`), never `mark_safe` raw content directly.
- **View conventions**: CRUD for most models uses generic class-based views (`ListView`/`DetailView`/`CreateView`/`UpdateView`/`DeleteView`) sharing two generic templates, `campanha/templates/campanha/generic_form.html` and `generic_confirm_delete.html` — add `titulo` and `cancel_url` to context via `get_context_data` rather than writing a bespoke template. Combat/PV/rest/resource actions are plain `@require_POST` function views that mutate state and redirect back to `combate` (see `campanha/views.py` — `atualizar_pv`, `aplicar_descanso`, `descanso_curto_dados`, `usar_recurso`).
- **Forms**: `BootstrapFormMixin` (`campanha/forms.py`) auto-applies Bootstrap CSS classes to widgets by type — apply it to any new `ModelForm` instead of setting widget classes by hand. `Pericia`/`Salvaguarda` are edited as `inlineformset_factory` formsets (`PericiaFormSet`/`SalvaguardaFormSet`) alongside the main `PersonagemForm` in `FichaEditView`.
- **Data sharing model**: `Personagem` (and its FK'd children: perícias, salvaguardas, recursos, itens, notas de combate) is per-character. `Local`, `NPC`, `Missao`, `ResumoSessao`, `InformacaoImportante` are campaign-wide/shared, not tied to a character.
