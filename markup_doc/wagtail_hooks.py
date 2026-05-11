from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from django.template.response import TemplateResponse
from wagtail_modeladmin.options import ModelAdmin

from wagtail.snippets.views.snippets import (
    CreateView,
    EditView,
    SnippetViewSet,
    SnippetViewSetGroup
)

from markup_doc.models import ( 
    ArticleDocx,
    ArticleDocxMarkup,
    UploadDocx,
    MarkupXML,
    CollectionModel,
    JournalModel,
    ProcessStatus
)

from markup_doc.tasks import get_labels, task_sync_journals_from_api
from wagtail.admin import messages

from wagtail.snippets.models import register_snippet
from django.db import transaction

from markup_doc.sync_api import sync_collection_from_api



@hooks.register('register_admin_urls')
def register_admin_urls():
    return [
        path('download-xml/<int:id_registro>/', views.generate_xml, name='generate_xml'),
        path('extract-citation/', views.extract_citation, name='extract_citation'),
        path('get_journal/', views.get_journal, name='get_journal'),
        path('download-zip/', views.generate_zip, name='generate_zip'),
        path('preview-html/', views.preview_html_post, name='preview_html_post'),
        path('pretty-xml/', views.preview_xml_tree, name='preview_xml_tree'),
    ]


@hooks.register('insert_editor_js')
def xref_js():
    return format_html(
        '<script src="{}"></script>',
        static('js/xref-button.js')
    )


class ArticleDocxCreateView(CreateView):
    # def get_form_class(self):
    def dispatch(self, request, *args, **kwargs):
        if not CollectionModel.objects.exists():
            messages.warning(request, "Debes seleccionar primero una colección.")
            return HttpResponseRedirect(self.get_success_url())
        if not JournalModel.objects.exists():
            messages.warning(
                request, "Espera un momento, aún no existen elementos en Journal."
            )
            return HttpResponseRedirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        self.object.estatus = ProcessStatus.PROCESSING
        self.object.save()
        transaction.on_commit(lambda: get_labels.delay(self.object.title, self.request.user.id))
        return HttpResponseRedirect(self.get_success_url())


class ArticleDocxEditView(EditView):
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        form.instance.save()
        update_xml.delay(form.instance.id, form.instance.content.get_prep_value(), form.instance.content_body.get_prep_value(), form.instance.content_back.get_prep_value())
        return HttpResponseRedirect(self.get_success_url())


class ArticleDocxAdmin(ModelAdmin):
    model = ArticleDocx
    create_view_class = ArticleDocxCreateView
    menu_label = _("Documents")
    menu_icon = "folder"
    menu_order = 1
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    list_per_page = 20
    list_display = ("title", "get_estatus_display")


class ArticleDocxMarkupCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class ArticleDocxMarkupAdmin(ModelAdmin):
    model = ArticleDocxMarkup
    create_view_class = ArticleDocxMarkupCreateView
    menu_label = _("Documents Markup")
    menu_icon = "folder"
    menu_order = 1
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    list_per_page = 20


class UploadDocxViewSet(SnippetViewSet):
    model = UploadDocx
    add_view_class = ArticleDocxCreateView
    menu_label = _("Carregar DOCX")
    menu_icon = "folder"
    menu_order = 1
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_per_page = 20
    list_display = ("title", "get_estatus_display")  # Usar estatus, não status
    search_fields = ("title",)
    list_filter = ("estatus",)  # Usar estatus, não status


class MarkupXMLViewSet(SnippetViewSet):
    model = MarkupXML
    add_view_class = ArticleDocxMarkupCreateView
    edit_view_class = ArticleDocxEditView
    menu_label = _("XML marcado")  # Alterado de "MarkupXML"
    menu_icon = "folder"
    menu_order = 1
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = ("title",)
    list_per_page = 20
    search_fields = ("title",)


class CollectionModelCreateView(CreateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sync_collection_from_api()
        return context

    def form_valid(self, form):
        form.instance.save()
        task_sync_journals_from_api.delay()
        return HttpResponseRedirect(self.get_success_url())


class CollectionModelViewSet(SnippetViewSet):
    model = CollectionModel
    add_view_class = CollectionModelCreateView
    menu_label = _("Modelo de Coleções")  # Alterado de "CollectionModel"
    menu_icon = "folder"
    menu_order = 1
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_per_page = 20
    list_display = ("collection",)


class JournalModelCreateView(CreateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        task_sync_journals_from_api
        return context


class JournalModelViewSet(SnippetViewSet):
    model = JournalModel
    menu_label = _("Modelo de Revistas")  # Alterado de "JournalModel"
    menu_icon = "folder"
    menu_order = 1
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_per_page = 20
    list_display = ("title",)

    def index_view(self, request):
        response = super().index_view(request)

        if isinstance(response, TemplateResponse):
            if not CollectionModel.objects.exists():
                messages.warning(request, "Debes seleccionar primero una colección.")
                response.context_data["can_add"] = False
                response.context_data["can_add_snippet"] = False
                return response

            if not JournalModel.objects.exists():
                messages.warning(
                    request,
                    "Sincronizando journals desde la API, espera unos momentos…",
                )
                response.context_data["can_add"] = False
                response.context_data["can_add_snippet"] = False
                return response

        return response


class MarkupSnippetViewSetGroup(SnippetViewSetGroup):
    menu_name = "docx_files"  # Renomeado de 'docx_processor'
    menu_label = _("DOCX Files")
    menu_icon = "folder-open-inverse"
    menu_order = 0  # Mudado de 1 para 0 para ficar na primeira posição
    items = (
        UploadDocxViewSet,
        MarkupXMLViewSet,
        CollectionModelViewSet,
        JournalModelViewSet,
    )


register_snippet(MarkupSnippetViewSetGroup)
