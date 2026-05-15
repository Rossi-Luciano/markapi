# Menu admin RCT, SVG, indexação, logo e correções Wagtail

**Data:** 2026-05-15  
**Branch:** `reorder_menu_enable_svg`

## Mensagem de commit

```
Reorganiza admin Wagtail, SVG, logo e indexação de imagens

Menu alinhado ao fluxo RCT; upload SVG; logo via admin_logo; corrige
title_text na indexação e imports em markup_doc/wagtail_hooks.
```

## O que esse PR faz?

Conjunto de melhorias no admin Wagtail e na configuração editorial do markapi:

### 1. Menu lateral (fluxo RCT)

Ordem centralizada em `config/menu.py`:

1. Marcação editorial (`markup_doc`)
2. Gestão de XML (`xml_manager`)
3. Referências bibliográficas (`reference`)
4. Rastreio de eventos (`tracker`)
5. Modelos de IA (`model_ai`)
6. Tarefas agendadas (`django_celery_beat`)

Rótulos e ícones atualizados em todos os `wagtail_hooks.py` dos módulos. Grupo **Marcação editorial**: Coleções → Periódicos → Carregar DOCX → XML SPS marcado. Removidos `ModelAdmin` legados não registados em `markup_doc`.

### 2. Upload de SVG

`WAGTAILIMAGES_EXTENSIONS` em `config/settings/base.py` inclui `svg` (e formatos raster habituais).

### 3. Logo do admin

Templates em `core_settings/templates/wagtailadmin/` usam `settings.core_settings.customsettings.admin_logo` na sidebar e no login. CSS em `core_settings/static/core_settings/css/admin_logo.css`. Fallback para logo Wagtail se não houver imagem.

### 4. Indexação de imagens (`title_text`)

Migração `core/migrations/0002_wagtailsearch_indexentry_text_defaults.py`: preenche `NULL` e define `DEFAULT ''` em `title_text`/`body_text` quando as colunas existem (corrige `IntegrityError` ao indexar imagens com schema Wagtail 7 e código de indexação que omite esses campos).

Signal em `core/wagtail_hooks.py`: define título da imagem a partir do nome do ficheiro quando vazio.

### 5. Correções em `markup_doc/wagtail_hooks.py`

Restaura imports (`path`, `format_html`, `static`, `TemplateResponse`, `update_xml`) e resolve conflito de merge.

## Onde a revisão poderia começar?

- [config/menu.py](config/menu.py)
- [markup_doc/wagtail_hooks.py](markup_doc/wagtail_hooks.py)
- [core_settings/templates/wagtailadmin/includes/admin_logo.html](core_settings/templates/wagtailadmin/includes/admin_logo.html)
- [core/migrations/0002_wagtailsearch_indexentry_text_defaults.py](core/migrations/0002_wagtailsearch_indexentry_text_defaults.py)

## Como este poderia ser testado manualmente?

1. `python manage.py migrate`
2. Reiniciar a aplicação e abrir `/admin/`
3. Confirmar ordem e rótulos do menu (Marcação editorial → … → Tarefas agendadas)
4. **Settings → Site configuration → Admin settings**: definir `admin_logo` (SVG) e recarregar admin — logo na sidebar e em `/admin/login/`
5. **Images**: upload de `.svg` sem erro
6. Se antes falhava indexação: repetir upload de logo e confirmar ausência de `IntegrityError` em `wagtailsearch_indexentry`

## Algum cenário de contexto que queira dar?

Alinhar versão instalada de `wagtail` com migrações já aplicadas na base (recomendado Wagtail 7.4 LTS se `wagtailsearch.0010_add_text_fields` existir). A migração em `core` mitiga desalinhamento entre schema e indexador. SVG em produção: restringir upload a utilizadores de confiança.

## Screenshots

N/A

## Quais são tickets relevantes?

N/A

## Referências

- SciELO RCT — `.cursor/rules/project-objectives.mdc`
- [Wagtail — customização do admin](https://docs.wagtail.org/en/stable/advanced_topics/customization/admin_templates.html)
- [Wagtail — SVG nas imagens](https://wagtail.org/blog/how-we-added-svg-support-to-wagtail-50/)
