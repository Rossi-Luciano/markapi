from django.db import transaction
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.templatetags.static import static
from django.urls import path
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin import messages
from wagtail_modeladmin.options import ModelAdmin
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import (
    CreateView,
    EditView,
    SnippetViewSet,
    SnippetViewSetGroup,
)

from config.menu import get_menu_order
from markup_doc import views
from markup_doc.models import (
    CollectionModel,
    JournalModel,
    MarkupXML,
    ProcessedDocx,
    ProcessStatus,
    UploadDocx,
)

from markup_doc import views
from markup_doc.sync_api import sync_collection_from_api
from markup_doc.tasks import get_labels, task_sync_journals_from_api, update_xml


@hooks.register("register_admin_urls")
def register_admin_urls():
    return [
        path(
            "download-xml/<int:id_registro>/", views.generate_xml, name="generate_xml"
        ),
        path(
            "download-marked-docx/<int:pk>/",
            views.download_marked_docx,
            name="download_marked_docx",
        ),
        path("reprocess/<int:pk>/", views.reprocess, name="reprocess"),
        path("extract-citation/", views.extract_citation, name="extract_citation"),
        path("get_journal/", views.get_journal, name="get_journal"),
        path("download-zip/", views.generate_zip, name="generate_zip"),
        path("preview-html/", views.preview_html_post, name="preview_html_post"),
        path("pretty-xml/", views.preview_xml_tree, name="preview_xml_tree"),
    ]


@hooks.register("insert_editor_js")
def xref_js():
    return format_html(
        '<script src="{}"></script>',
        static("js/xref-button.js"),
    )


class ArticleDocxCreateView(CreateView):
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
        transaction.on_commit(
            lambda: get_labels.delay(self.object.title, self.request.user.id)
        )
        return HttpResponseRedirect(self.get_success_url())


class ArticleDocxEditView(EditView):
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        form.instance.save()
        update_xml.delay(
            form.instance.id,
            form.instance.content.get_prep_value(),
            form.instance.content_body.get_prep_value(),
            form.instance.content_back.get_prep_value(),
        )
        return HttpResponseRedirect(self.get_success_url())


class ArticleDocxMarkupCreateView(CreateView):
    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class UploadDocxViewSet(SnippetViewSet):
    model = UploadDocx
    add_view_class = ArticleDocxCreateView
    menu_label = _("Carregar DOCX")
    menu_icon = "upload"
    add_to_admin_menu = False
    exclude_from_explorer = False
    list_per_page = 20
    list_display = ("title", "get_estatus_display")
    search_fields = ("title",)
    list_filter = ("estatus",)


class MarkupXMLViewSet(SnippetViewSet):
    model = MarkupXML
    add_view_class = ArticleDocxMarkupCreateView
    edit_view_class = ArticleDocxEditView
    menu_label = _("XML SPS marcado")
    menu_icon = "code"
    add_to_admin_menu = False
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
    menu_label = _("Coleções SciELO")
    menu_icon = "folder-inverse"
    add_to_admin_menu = False
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
    menu_label = _("Periódicos")
    menu_icon = "doc-empty"
    add_to_admin_menu = False
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


class ProcessedDocxViewSet(SnippetViewSet):
    model = ProcessedDocx
    menu_label = _("DOCX processado")
    menu_icon = "doc-full-inverse"
    add_to_admin_menu = False
    exclude_from_explorer = False
    list_per_page = 20
    list_display = ("title", "get_estatus_display", "get_marked_file_status")
    search_fields = ("title",)
    list_filter = ("estatus",)


class MarkupSnippetViewSetGroup(SnippetViewSetGroup):
    menu_name = "markup_doc"
    menu_label = _("Marcação editorial")
    menu_icon = "edit"
    menu_order = get_menu_order("markup_doc")
    items = (
        CollectionModelViewSet,
        JournalModelViewSet,
        UploadDocxViewSet,
        ProcessedDocxViewSet,
        MarkupXMLViewSet,
    )


register_snippet(MarkupSnippetViewSetGroup)
