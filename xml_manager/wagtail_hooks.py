import os

from django.urls import path, include
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin.ui.tables import Column
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from config.menu import get_menu_order

from .models import XMLDocument, XMLDocumentPDF, XMLDocumentHTML
from . import urls


class FileNameColumn(Column):
    """
    Coluna que mostra apenas o nome do arquivo de um FileField.
    """
    def get_value(self, instance):
        val = super().get_value(instance)
        if not val:
            return "-"
        return os.path.basename(getattr(val, "name", str(val)))


class LinkColumn(Column):
    """
    Column que recebe um FileField (FieldFile) e renderiza um <a href>.
    Cria '-' se não houver arquivo.
    """
    def get_value(self, instance):
        val = super().get_value(instance)
        if not val:
            return "-"
        name = os.path.basename(getattr(val, "name", str(val)))
        try:
            url = val.url
        except Exception:
            return name
        return format_html('<a href="{}" target="_blank">{}</a>', url, name)


class ActionColumn(Column):
    def get_value(self, instance):
        url = reverse("process_xml_pk", args=[instance.pk])
        return format_html(
            '<a href="{}" class="button button-small">Processar</a>', url
        )


class XMLDocumentSnippetViewSet(SnippetViewSet):
    model = XMLDocument
    verbose_name = _("XML Document")
    verbose_name_plural = _("XML Documents")
    icon = "folder-open-inverse"
    menu_name = "xml_files"
    menu_label = _("XML Document")
    menu_order = get_menu_order("xml_files")
    add_to_admin_menu = False

    list_display = (
        "xml_file",
        LinkColumn("validation_file", label=_("Validation file")),
        LinkColumn("exceptions_file", label=_("Exceptions file")),
        "uploaded_at",
        ActionColumn("actions", label=_("Action")),
    )

    search_fields = ("xml_file",)
    list_filter = ("uploaded_at",)


class XMLDocumentPDFSnippetViewSet(SnippetViewSet):
    model = XMLDocumentPDF
    verbose_name = _("XML Document PDF")
    verbose_name_plural = _("XML Document PDFs")
    icon = "doc-full"
    menu_name = "xml_files"
    menu_label = _("XML Document PDF")
    menu_order = get_menu_order("xml_files")
    add_to_admin_menu = False

    list_display = (
        "xml_document",
        LinkColumn("pdf_file", "PDF file"),
        LinkColumn("docx_file", "DOCX file"),
        "language",
        "uploaded_at"
    )

    search_fields = ("pdf_file", "language")
    list_filter = ("language", "uploaded_at")


class XMLDocumentHTMLSnippetViewSet(SnippetViewSet):
    model = XMLDocumentHTML
    verbose_name = _("XML Document HTML")
    verbose_name_plural = _("XML Document HTMLs")
    icon = "doc-full"
    menu_name = "xml_files"
    menu_label = _("XML Document HTML")
    menu_order = get_menu_order("xml_files")
    add_to_admin_menu = False

    list_display = (
        "xml_document",
        LinkColumn("html_file", "HTML file"),
        "language",
        "uploaded_at",
    )

    search_fields = ("html_file", "language")
    list_filter = ("language", "uploaded_at")


class XMLDocumentSnippetViewSetGroup(SnippetViewSetGroup):
    menu_name = 'xml_files'
    menu_label = _("XML Files")
    menu_icon = "folder-open-inverse"
    menu_order = 0
    # menu_order = get_menu_order("xml_files")
    items = (
        XMLDocumentSnippetViewSet,
        XMLDocumentHTMLSnippetViewSet,
        XMLDocumentPDFSnippetViewSet,
    )


register_snippet(XMLDocumentSnippetViewSetGroup)


@hooks.register('register_admin_urls')
def register_admin_urls():
    return [
        path('xml-files/', include(urls)),
    ]