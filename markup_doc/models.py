import json
import os

from django import forms
from django.db import models
from django.urls import reverse
from django.utils.html import format_html, mark_safe
from django.utils.translation import gettext_lazy as _
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, ObjectList, Panel, TabbedInterface
from wagtail.blocks import ChoiceBlock, StreamBlock, StructBlock, TextBlock
from wagtail.fields import StreamField
from wagtail.images.blocks import ImageChooserBlock
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.choices import LANGUAGE
from core.forms import CoreAdminModelForm
from core.models import CommonControlField

from .choices import front_labels


class ProcessStatus(models.IntegerChoices):
    PROCESSING = 1, _("Processing")
    PROCESSED = 2, _("Processed")


class ReadOnlyFileWidget(forms.Widget):
    def render(self, name, value, attrs=None, renderer=None):
        if value:
            instance = value.instance
            url = reverse("generate_xml", args=[instance.pk])
            return format_html(
                '<a href="{}" target="_blank" download>Download XML</a>', url
            )
        return ""


class DownloadMarkedFileWidget(forms.Widget):
    def render(self, name, value, attrs=None, renderer=None):
        if value:
            instance = value.instance
            url = reverse("download_marked_docx", args=[instance.pk])
            filename = os.path.basename(value.name)
            return format_html(
                '<a href="{}" target="_blank" download>{}</a>', url, filename
            )
        return mark_safe('<span style="color: gray;">Não disponível ainda</span>')


class XrefStatusWidget(forms.Widget):
    def render(self, name, value, attrs=None, renderer=None):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, ValueError):
                value = None
        if not value:
            return mark_safe('<span style="color: gray;">Não processado</span>')
        valid = value.get("valid", False)
        total_refs = value.get("total_references", 0)
        total_cits = value.get("total_citations", 0)
        orphaned_bk = len(value.get("orphaned_bookmarks", []))
        orphaned_hl = value.get("orphaned_hyperlinks", [])
        color = "green" if valid else "red"
        status = "Válido" if valid else "Inválido"
        html = format_html(
            '<p><strong style="color:{};">{}</strong> &nbsp; {} referências | {} citações linkadas</p>',
            color, status, total_refs, total_cits,
        )
        if orphaned_hl:
            html += format_html(
                '<p style="color:red;">Citações sem referência: {}</p>',
                ', '.join(orphaned_hl),
            )
        if orphaned_bk:
            html += format_html(
                '<p style="color:orange;">{} referência(s) sem citação no texto</p>',
                orphaned_bk,
            )
        return html


class ReprocessButtonPanel(Panel):
    def __init__(self, confirm_message="Reprocessar este documento?", **kwargs):
        super().__init__(**kwargs)
        self.confirm_message = confirm_message

    def clone_kwargs(self):
        return {**super().clone_kwargs(), "confirm_message": self.confirm_message}

    class BoundPanel(Panel.BoundPanel):
        def render_html(self, parent_context=None):
            if not self.instance or not self.instance.pk:
                return ""
            url = reverse("reprocess", args=[self.instance.pk])
            msg = self.panel.confirm_message.replace("'", "\\'")
            return mark_safe(
                f'<div style="margin:12px 0;">'
                f'<a href="{url}" onclick="return confirm(\'{msg}\')" '
                f'style="padding:8px 16px;background:#e9a000;color:white;'
                f'font-weight:bold;border-radius:4px;text-decoration:none;">'
                f'Reprocessar</a></div>'
            )


class ArticleDocx(CommonControlField):
    title = models.TextField(_("Document Title"), null=True, blank=True)
    file = models.FileField(
        null=True,
        blank=True,
        verbose_name=_("Document"),
        upload_to="uploads_docx/",
    )
    estatus = models.IntegerField(
        _("Process estatus"),
        choices=ProcessStatus.choices,
        blank=True,
        default=ProcessStatus.PROCESSING,
    )

    panels = [
        FieldPanel("title"),
        FieldPanel("file"),
    ]

    base_form_class = CoreAdminModelForm

    def __unicode__(self):
        return f"{self.title} | {self.estatus}"

    def __str__(self):
        title = self.title or ""
        return f"{title} | {self.estatus}"

    @classmethod
    def get(cls, title):
        return cls.objects.get(title=title)

    @classmethod
    def update(cls, title, estatus):
        try:
            obj = cls.get(title=title)
        except (cls.DoesNotExist, ValueError):
            return None

        obj.estatus = estatus
        obj.save()
        return obj


class ParagraphWithLanguageBlock(StructBlock):
    label = ChoiceBlock(choices=front_labels, required=False, label=_("Label"))
    language = ChoiceBlock(choices=LANGUAGE, required=False, label="Language")
    paragraph = TextBlock(required=False, label=_("Title"))

    class Meta:
        label = _("Paragraph with Language")


class ParagraphBlock(StructBlock):
    label = ChoiceBlock(choices=front_labels, required=False, label=_("Label"))
    paragraph = TextBlock(required=False, label=_("Paragraph"))

    class Meta:
        label = _("Paragraph")


class CompoundParagraphBlock(StructBlock):
    label = ChoiceBlock(choices=front_labels, required=False, label=_("Label"))
    eid = TextBlock(required=False, label=_("Equation id"))
    content = StreamBlock(
        [
            ("text", TextBlock(label=_("Text"))),
            ("formula", TextBlock(label=_("Formula"))),
        ],
        label=_("Content"),
        required=True,
    )

    class Meta:
        label = _("Compound paragraph")


class ImageBlock(StructBlock):
    label = ChoiceBlock(choices=front_labels, required=False, label=_("Label"))
    figid = TextBlock(required=False, label=_("Fig id"))
    figlabel = TextBlock(required=False, label=_("Fig label"))
    title = TextBlock(required=False, label=_("Title"))
    alttext = TextBlock(required=False, label=_("Alt text"))
    image = ImageChooserBlock(required=True)

    class Meta:
        label = _("Image")


class TableBlock(StructBlock):
    label = ChoiceBlock(choices=front_labels, required=False, label=_("Label"))
    tabid = TextBlock(required=False, label=_("Table id"))
    tablabel = TextBlock(required=False, label=_("Table label"))
    title = TextBlock(required=False, label=_("Title"))
    content = TextBlock(required=False, label=_("Content"))

    class Meta:
        label = _("Table")


class AuthorParagraphBlock(ParagraphBlock):
    surname = TextBlock(required=False, label=_("Surname"))
    given_names = TextBlock(required=False, label=_("Given names"))
    orcid = TextBlock(required=False, label=_("Orcid"))
    affid = TextBlock(required=False, label=_("Aff id"))
    char = TextBlock(required=False, label=_("Char link"))

    class Meta:
        label = _("Author Paragraph")


class AffParagraphBlock(ParagraphBlock):
    affid = TextBlock(required=False, label=_("Aff id"))
    text_aff = TextBlock(required=False, label=_("Full text Aff"))
    char = TextBlock(required=False, label=_("Char link"))
    orgname = TextBlock(required=False, label=_("Orgname"))
    orgdiv2 = TextBlock(required=False, label=_("Orgdiv2"))
    orgdiv1 = TextBlock(required=False, label=_("Orgdiv1"))
    zipcode = TextBlock(required=False, label=_("Zipcode"))
    city = TextBlock(required=False, label=_("City"))
    state = TextBlock(required=False, label=_("State"))
    country = TextBlock(required=False, label=_("Country"))
    code_country = TextBlock(required=False, label=_("Code country"))
    original = TextBlock(required=False, label=_("Original"))

    class Meta:
        label = _("Aff Paragraph")


class RefNameBlock(StructBlock):
    surname = TextBlock(required=False, label=_("Surname"))
    given_names = TextBlock(required=False, label=_("Given names"))


class RefParagraphBlock(ParagraphBlock):
    reftype = TextBlock(required=False, label=_("Ref type"))
    refid = TextBlock(required=False, label=_("Ref id"))
    # authors = ListBlock(RefNameBlock(), label=_("Authors"))
    authors = StreamBlock(
        [
            ("Author", RefNameBlock()),
        ],
        label=_("Authors"),
        required=False,
    )
    date = TextBlock(required=False, label=_("Date"))
    title = TextBlock(required=False, label=_("Title"))
    chapter = TextBlock(required=False, label=_("Chapter"))
    edition = TextBlock(required=False, label=_("Edition"))
    source = TextBlock(required=False, label=_("Source"))
    vol = TextBlock(required=False, label=_("Vol"))
    issue = TextBlock(required=False, label=_("Issue"))
    pages = TextBlock(required=False, label=_("Pages"))
    fpage = TextBlock(required=False, label=_("First page"))
    lpage = TextBlock(required=False, label=_("Last page"))
    doi = TextBlock(required=False, label=_("DOI"))
    access_id = TextBlock(required=False, label=_("Access id"))
    degree = TextBlock(required=False, label=_("Degree"))
    organization = TextBlock(required=False, label=_("Organization"))
    location = TextBlock(required=False, label=_("Location"))
    org_location = TextBlock(required=False, label=_("Org location"))
    num_pages = TextBlock(required=False, label=_("Num pages"))
    uri = TextBlock(required=False, label=_("Uri"))
    version = TextBlock(required=False, label=_("Version"))
    access_date = TextBlock(required=False, label=_("Access date"))

    class Meta:
        label = _("Ref Paragraph")


class CollectionValuesModel(models.Model):
    acron = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=255)

    autocomplete_search_field = "acron"

    def autocomplete_label(self):
        return str(self)

    def __str__(self):
        return f"{self.acron.upper()} - {self.name}"


class CollectionModel(models.Model):
    collection = models.ForeignKey(
        CollectionValuesModel, null=True, blank=True, on_delete=models.SET_NULL
    )

    autocomplete_search_field = "collection.acron"

    def autocomplete_label(self):
        return str(self)

    panels = [
        AutocompletePanel("collection"),
    ]

    def __str__(self):
        if not self.collection:
            return ""
        acron = self.collection.acron or ""
        return f"{acron.upper()} - {acron}"


class JournalModel(models.Model):
    title = models.TextField(_("Title"), null=True, blank=True)
    short_title = models.TextField(_("Short Title"), null=True, blank=True)
    title_nlm = models.TextField(_("NLM Title"), null=True, blank=True)
    acronym = models.TextField(_("Acronym"), null=True, blank=True)
    issn = models.TextField(_("ISSN (id SciELO)"), null=True, blank=True)
    pissn = models.TextField(_("Print ISSN"), null=True, blank=True)
    eissn = models.TextField(_("Electronic ISSN"), null=True, blank=True)
    pubname = models.TextField(_("Publisher Name"), null=True, blank=True)

    autocomplete_search_field = "title"

    class Meta:
        unique_together = ("title",)

    def autocomplete_label(self):
        return str(self)

    def __str__(self):
        return self.title or ""


def get_default_collection_acron():
    try:
        obj = CollectionModel.objects.select_related("collection").first()
        return obj.collection.acron if obj and obj.collection else ""
    except Exception:
        return ""


class ArticleDocxMarkup(CommonControlField, ClusterableModel):
    title = models.TextField(_("Document Title"), null=True, blank=True)
    file = models.FileField(
        null=True,
        blank=True,
        verbose_name=_("Document"),
        upload_to="uploads_docx/",
    )
    marked_file = models.FileField(
        null=True,
        blank=True,
        verbose_name=_("Marked Document"),
        upload_to="uploads_docx_marked/",
    )
    xref_status = models.JSONField(
        _("XRef Status"),
        null=True,
        blank=True,
    )
    estatus = models.IntegerField(
        _("Process estatus"),
        choices=ProcessStatus.choices,
        blank=True,
        default=ProcessStatus.PROCESSING,
    )

    collection = models.CharField(max_length=10, default=get_default_collection_acron)
    journal = models.ForeignKey(
        JournalModel, null=True, blank=True, on_delete=models.SET_NULL
    )

    journal_title = models.TextField(_("Journal Title"), null=True, blank=True)
    acronym = models.TextField(_("Acronym"), null=True, blank=True)
    short_title = models.TextField(_("Short Title"), null=True, blank=True)
    title_nlm = models.TextField(_("NLM Title"), null=True, blank=True)
    issn = models.TextField(_("ISSN (id SciELO)"), null=True, blank=True)
    pissn = models.TextField(_("Print ISSN"), null=True, blank=True)
    eissn = models.TextField(_("Electronic ISSN"), null=True, blank=True)
    nimtitle = models.TextField(_("Nimtitle"), null=True, blank=True)
    pubname = models.TextField(_("Publisher Name"), null=True, blank=True)
    license = models.URLField(
        max_length=500, blank=True, null=True, verbose_name=_("License (URL)")
    )
    vol = models.IntegerField(verbose_name=_("Volume"), null=True, blank=True)
    supplvol = models.IntegerField(
        verbose_name=_("Suppl Volume"), null=True, blank=True
    )
    issue = models.IntegerField(verbose_name=_("Issue"), null=True, blank=True)
    supplno = models.IntegerField(verbose_name=_("Suppl Num"), null=True, blank=True)
    issid_part = models.TextField(_("Isid Part"), null=True, blank=True)
    dateiso = models.TextField(_("Dateiso"), null=True, blank=True)
    month = models.TextField(_("Month/Season"), null=True, blank=True)
    fpage = models.TextField(_("First Page"), null=True, blank=True)
    seq = models.TextField(_("@Seq"), null=True, blank=True)
    lpage = models.TextField(_("Last Page"), null=True, blank=True)
    elocatid = models.TextField(_("Elocation ID"), null=True, blank=True)
    order = models.TextField(_("Order (In TOC)"), null=True, blank=True)
    pagcount = models.TextField(_("Pag count"), null=True, blank=True)
    doctopic = models.TextField(_("Doc Topic"), null=True, blank=True)
    language = models.CharField(
        _("Language"), max_length=10, choices=LANGUAGE, null=True, blank=True
    )
    spsversion = models.TextField(_("Sps version"), null=True, blank=True)
    artdate = models.DateField(_("Artdate"), null=True, blank=True)
    ahpdate = models.DateField(_("Ahpdate"), null=True, blank=True)

    file_xml = models.FileField(
        null=True,
        blank=True,
        verbose_name=_("Document xml"),
        upload_to="generate_xml/",
    )

    text_xml = models.TextField(_("Text XML"), null=True, blank=True)

    content = StreamField(
        [
            ("paragraph_with_language", ParagraphWithLanguageBlock()),
            ("paragraph", ParagraphBlock()),
            ("author_paragraph", AuthorParagraphBlock()),
            ("aff_paragraph", AffParagraphBlock()),
        ],
        blank=True,
        use_json_field=True,
    )

    content_body = StreamField(
        [
            ("paragraph", ParagraphBlock()),
            ("paragraph_with_language", ParagraphWithLanguageBlock()),
            ("compound_paragraph", CompoundParagraphBlock()),
            ("image", ImageBlock()),
            ("table", TableBlock()),
        ],
        blank=True,
        use_json_field=True,
    )

    content_back = StreamField(
        [
            ("paragraph", ParagraphBlock()),
            ("ref_paragraph", RefParagraphBlock()),
        ],
        blank=True,
        use_json_field=True,
    )

    panels = [
        FieldPanel("title"),
        FieldPanel("file"),
        FieldPanel("collection"),
        AutocompletePanel("journal"),
    ]

    def __unicode__(self):
        return f"{self.title} | {self.estatus}"

    def __str__(self):
        title = self.title or ""
        return f"{title} | {self.estatus}"

    def get_marked_file_status(self):
        if not self.marked_file:
            return "Aguardando processamento"
        if self.xref_status:
            total = self.xref_status.get("total_references", 0)
            cits = self.xref_status.get("total_citations", 0)
            return f"✓ Disponível ({total} refs, {cits} citações)"
        return "✓ Disponível"
    get_marked_file_status.short_description = _("DOCX Marcado")

    @property
    def url_download(self):
        return self.file_xml.url if self.file_xml else None

    @classmethod
    def create(cls, title):
        obj = cls()
        obj.title = title
        obj.save()
        return obj

    @classmethod
    def get(cls, title):
        return cls.objects.get(title=title)

    @classmethod
    def update(cls, title, estatus):
        try:
            obj = cls.get(title=title)
        except (cls.DoesNotExist, ValueError):
            return None

        obj.estatus = estatus
        obj.save()
        return obj

    base_form_class = CoreAdminModelForm


class UploadDocx(ArticleDocxMarkup):
    panels_doc = [
        FieldPanel("title"),
        FieldPanel("file"),
    ]

    edit_handler = TabbedInterface(
        [
            ObjectList(panels_doc, heading=_("Document")),
        ]
    )

    class Meta:
        proxy = True


class MarkupXML(ArticleDocxMarkup):
    panels_front = [
        FieldPanel("content"),
        # InlinePanel("element_docx", label=_("Elements Docx")),
    ]

    panels_body = [
        FieldPanel("content_body"),
    ]

    panels_back = [
        FieldPanel("content_back"),
    ]

    panels_xml = [
        FieldPanel("file_xml", widget=ReadOnlyFileWidget()),
        FieldPanel("text_xml"),
        ReprocessButtonPanel(
            confirm_message="Isso irá descartar as edições manuais e reprocessar o DOCX original. Continuar?"
        ),
    ]

    panels_details = [
        FieldPanel("collection"),
        AutocompletePanel("journal"),
        FieldPanel("journal_title"),
        FieldPanel("short_title"),
        FieldPanel("title_nlm"),
        FieldPanel("acronym"),
        FieldPanel("issn"),
        FieldPanel("pissn"),
        FieldPanel("eissn"),
        FieldPanel("nimtitle"),
        FieldPanel("pubname"),
        FieldPanel("license"),
        FieldPanel("vol"),
        FieldPanel("supplvol"),
        FieldPanel("issue"),
        FieldPanel("supplno"),
        FieldPanel("issid_part"),
        FieldPanel("dateiso"),
        FieldPanel("month"),
        FieldPanel("fpage"),
        FieldPanel("seq"),
        FieldPanel("lpage"),
        FieldPanel("elocatid"),
        FieldPanel("order"),
        FieldPanel("pagcount"),
        FieldPanel("doctopic"),
        FieldPanel("language"),
        FieldPanel("spsversion"),
        FieldPanel("artdate"),
        FieldPanel("ahpdate"),
    ]

    edit_handler = TabbedInterface(
        [
            ObjectList(panels_xml, heading="XML"),
            ObjectList(panels_details, heading=_("Details")),
            ObjectList(panels_front, heading="Front"),
            ObjectList(panels_body, heading="Body"),
            ObjectList(panels_back, heading="Back"),
        ]
    )

    class Meta:
        proxy = True


class ProcessedDocx(ArticleDocxMarkup):
    panels_doc = [
        FieldPanel("title"),
        FieldPanel("marked_file", widget=DownloadMarkedFileWidget()),
        FieldPanel("xref_status", widget=XrefStatusWidget()),
        ReprocessButtonPanel(confirm_message="Reprocessar este documento?"),
    ]

    edit_handler = TabbedInterface([
        ObjectList(panels_doc, heading=_("DOCX Marcado")),
    ])

    class Meta:
        proxy = True
        verbose_name = _("DOCX processado")
        verbose_name_plural = _("DOCXs processados")
