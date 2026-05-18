import os

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import include, path, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin.ui.tables import Column
from wagtail.admin.widgets.button import Button
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import (
    CreateView,
    EditView,
    SnippetViewSet,
    SnippetViewSetGroup,
)

from config.menu import get_menu_order

from . import urls
from .forms import SPSPackageValidationForm
from .models import (
    SPSPackageValidation,
    SPSPackageValidationStatus,
    XMLDocument,
    XMLDocumentHTML,
    XMLDocumentPDF,
)



class FileNameColumn(Column):
    def get_value(self, instance):
        val = super().get_value(instance)
        if not val:
            return "-"
        return os.path.basename(getattr(val, "name", str(val)))


class LinkColumn(Column):
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


class WagtailDocumentLinkColumn(Column):
    def get_value(self, instance):
        doc = super().get_value(instance)
        if not doc:
            return "-"
        try:
            url = doc.url
        except Exception:
            url = doc.file.url
        return format_html('<a href="{}" target="_blank">{}</a>', url, doc.title)


class ActionColumn(Column):
    def get_value(self, instance):
        url = reverse("process_xml_pk", args=[instance.pk])
        return format_html(
            '<a href="{}" class="button button-small">Processar</a>', url
        )


class SPSPackageValidationCreateView(CreateView):
    def get_form_class(self):
        return SPSPackageValidationForm

    def form_valid(self, form):
        zip_upload = form.cleaned_data["zip_upload"]
        document = SPSPackageValidationForm.save_wagtail_document(zip_upload)
        validation = SPSPackageValidation(
            package_document=document,
            status=SPSPackageValidationStatus.PENDING,
            zip_size_bytes=zip_upload.size,
            validated_by=self.request.user,
        )
        validation.save()
        self.object = validation
        # TODO: here add the code to validate the package
        
        messages.success(
            self.request,
            _("SPS package uploaded. Validation started for “%(title)s”.")
            % {"title": document.title},
        )
        return HttpResponseRedirect(self.get_success_url())


class SPSPackageValidationEditView(EditView):
    def get_form_class(self):
        return SPSPackageValidationForm

    def form_valid(self, form):
        validation = form.instance
        zip_upload = form.cleaned_data.get("zip_upload")
        if zip_upload:
            validation.package_document.file.save(
                zip_upload.name, zip_upload, save=True
            )
            validation.package_document.save()
            validation.zip_size_bytes = zip_upload.size
            if validation.validation_document:
                validation.validation_document.delete()
                validation.validation_document = None
            if validation.exceptions_document:
                validation.exceptions_document.delete()
                validation.exceptions_document = None
        validation.status = SPSPackageValidationStatus.PENDING
        validation.validated_by = self.request.user
        validation.validated_at = None
        validation.error_message = ""
        validation.save()
        self.object = validation
        # TODO: here add the code to validate the package
        
        messages.success(
            self.request,
            _("Validation started for “%(title)s”.") % {"title": validation},
        )
        return HttpResponseRedirect(self.get_success_url())


class XMLDocumentSnippetViewSet(SnippetViewSet):
    model = XMLDocument
    verbose_name = _("XML Document")
    verbose_name_plural = _("XML Documents")
    icon = "folder-open-inverse"
    menu_name = "xml_manager"
    menu_label = _("Documentos XML")
    add_to_admin_menu = False

    list_display = (
        "xml_file",
        LinkColumn("validation_file", label=_("Validation file")),
        LinkColumn("exceptions_file", label=_("Exceptions file")),
        "uploaded_at",
        ActionColumn("actions", label=_("Action")),
    )

    search_fields = ("xml_file",)


class XMLDocumentPDFSnippetViewSet(SnippetViewSet):
    model = XMLDocumentPDF
    verbose_name = _("XML Document PDF")
    verbose_name_plural = _("XML Document PDFs")
    icon = "doc-full"
    menu_name = "xml_manager"
    menu_label = _("PDF derivados")
    menu_icon = "doc-full"
    add_to_admin_menu = False

    list_display = (
        "xml_document",
        LinkColumn("pdf_file", "PDF file"),
        LinkColumn("docx_file", "DOCX file"),
        "language",
        "uploaded_at",
    )

    search_fields = ("pdf_file",)


class XMLDocumentHTMLSnippetViewSet(SnippetViewSet):
    model = XMLDocumentHTML
    verbose_name = _("XML Document HTML")
    verbose_name_plural = _("XML Document HTMLs")
    icon = "doc-full"
    menu_name = "xml_manager"
    menu_label = _("HTML derivados")
    menu_icon = "doc-full-inverse"
    add_to_admin_menu = False

    list_display = (
        "xml_document",
        LinkColumn("html_file", "HTML file"),
        "language",
        "uploaded_at",
    )

    search_fields = ("html_file",)


class SPSPackageValidationSnippetViewSet(SnippetViewSet):
    model = SPSPackageValidation
    add_view_class = SPSPackageValidationCreateView
    edit_view_class = SPSPackageValidationEditView
    copy_view_enabled = False
    verbose_name = _("SPS package validation")
    verbose_name_plural = _("Validar pacote SPS")
    icon = "doc-full-inverse"
    menu_name = "sps_package_validation"
    menu_label = _("Validar pacote SPS")
    add_to_admin_menu = False

    list_display = (
        "__str__",
        WagtailDocumentLinkColumn("package_document", label=_("SPS package (ZIP)")),
        "zip_size_bytes",
        "validated_by",
        "validated_at",
        "status",
        WagtailDocumentLinkColumn("validation_document", label=_("Validation file")),
        WagtailDocumentLinkColumn("exceptions_document", label=_("Exceptions file")),
    )

    list_filter = ("status",)
    search_fields = ("package_document__title",)


class XMLDocumentSnippetViewSetGroup(SnippetViewSetGroup):
    menu_name = "xml_manager"
    menu_label = _("Gestão de XML")
    menu_icon = "code"
    menu_order = get_menu_order("xml_manager")
    items = (
        XMLDocumentSnippetViewSet,
        XMLDocumentPDFSnippetViewSet,
        XMLDocumentHTMLSnippetViewSet,
        SPSPackageValidationSnippetViewSet,
    )


register_snippet(XMLDocumentSnippetViewSetGroup)


@hooks.register("register_admin_urls")
def register_admin_urls():
    return [
        path("xml-manager/", include(urls)),
    ]


@hooks.register("register_snippet_listing_buttons")
def sps_package_validation_listing_buttons(snippet, user, next_url=None):
    if not isinstance(snippet, SPSPackageValidation):
        return
    yield Button(
        _("Revalidar"),
        reverse("revalidate_sps_package_pk", args=[snippet.pk]),
        icon_name="rotate",
        priority=25,
    )
