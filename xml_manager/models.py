from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel


class SPSPackageValidationStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    RUNNING = "running", _("Running")
    DONE = "done", _("Done")
    ERROR = "error", _("Error")


class XMLDocument(models.Model):
    xml_file = models.FileField(
        upload_to="xml_manager/xml/",
        verbose_name=_("XML File"),
        help_text=_("Upload an XML file for processing."),
    )
    validation_file = models.FileField(
        upload_to="xml_manager/validation/",
        blank=True,
        null=True,
        verbose_name=_("Validation File"),
    )
    exceptions_file = models.FileField(
        upload_to="xml_manager/validation/",
        blank=True,
        null=True,
        verbose_name=_("Exceptions File"),
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Uploaded At"),
        help_text=_("The date and time when the file was uploaded."),
    )

    panels = [
        FieldPanel("xml_file"),
    ]

    def __str__(self):
        return f"{self.xml_file.name}"

    class Meta:
        verbose_name = _("XML Document")
        verbose_name_plural = _("XML Documents")


class XMLDocumentPDF(models.Model):
    xml_document = models.ForeignKey(
        XMLDocument,
        on_delete=models.CASCADE,
        related_name="pdfs",
        verbose_name=_("XML Document"),
    )
    pdf_file = models.FileField(
        upload_to="xml_manager/pdf/", verbose_name=_("PDF File")
    )
    docx_file = models.FileField(
        upload_to="xml_manager/docx/",
        verbose_name=_("DOCX File"),
        null=True,
        blank=True,
        help_text=_("Intermediate DOCX file generated during PDF creation"),
    )
    language = models.CharField(
        max_length=32,
        default="pt",
        verbose_name=_("Language"),
        help_text=_("Language code or name"),
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Uploaded At"))

    def __str__(self):
        return f"PDF for {self.xml_document.xml_file.name} ({self.language})"

    class Meta:
        verbose_name = _("XML Document PDF")
        verbose_name_plural = _("XML Document PDFs")

    @classmethod
    def create(cls, xml_document, pdf_file, language="pt"):
        pdf_instance = cls(
            xml_document=xml_document, pdf_file=pdf_file, language=language
        )
        pdf_instance.save()
        return pdf_instance


class XMLDocumentHTML(models.Model):
    xml_document = models.ForeignKey(
        XMLDocument,
        on_delete=models.CASCADE,
        related_name="htmls",
        verbose_name=_("XML Document"),
    )
    html_file = models.FileField(
        upload_to="xml_manager/html/", verbose_name=_("HTML File")
    )
    language = models.CharField(
        max_length=32,
        default="pt",
        verbose_name=_("Language"),
        help_text=_("Language code or name"),
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Uploaded At"))

    def __str__(self):
        return f"HTML for {self.xml_document.xml_file.name} ({self.language})"

    class Meta:
        verbose_name = _("XML Document HTML")
        verbose_name_plural = _("XML Document HTMLs")

    @classmethod
    def create(cls, xml_document, html_file, language="pt"):
        html_instance = cls(
            xml_document=xml_document, html_file=html_file, language=language
        )
        html_instance.save()
        return html_instance


class XMLDocumentPubMed(models.Model):
    xml_document = models.ForeignKey(
        XMLDocument,
        on_delete=models.CASCADE,
        related_name="pubmeds",
        verbose_name=_("XML Document"),
    )
    pubmed_file = models.FileField(
        upload_to="xml_manager/pubmed/", verbose_name=_("PubMed XML File")
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Uploaded At"))

    def __str__(self):
        return f"PubMed XML for {self.xml_document.xml_file.name}"

    class Meta:
        verbose_name = _("XML Document PubMed")
        verbose_name_plural = _("XML Document PubMeds")

    @classmethod
    def create(cls, xml_document, pubmed_file):
        instance = cls(xml_document=xml_document, pubmed_file=pubmed_file)
        instance.save()
        return instance


class XMLDocumentPMC(models.Model):
    xml_document = models.ForeignKey(
        XMLDocument,
        on_delete=models.CASCADE,
        related_name="pmcs",
        verbose_name=_("XML Document"),
    )
    pmc_file = models.FileField(
        upload_to="xml_manager/pmc/", verbose_name=_("PMC XML File")
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Uploaded At"))

    def __str__(self):
        return f"PMC XML for {self.xml_document.xml_file.name}"

    class Meta:
        verbose_name = _("XML Document PMC")
        verbose_name_plural = _("XML Document PMCs")

    @classmethod
    def create(cls, xml_document, pmc_file):
        instance = cls(xml_document=xml_document, pmc_file=pmc_file)
        instance.save()
        return instance


class SPSPackageValidation(models.Model):
    package_document = models.OneToOneField(
        "wagtaildocs.Document",
        on_delete=models.CASCADE,
        related_name="sps_validation",
        verbose_name=_("SPS package document"),
    )
    validation_document = models.ForeignKey(
        "wagtaildocs.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Validation file"),
    )
    exceptions_document = models.ForeignKey(
        "wagtaildocs.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Exceptions file"),
    )
    zip_size_bytes = models.PositiveBigIntegerField(
        verbose_name=_("ZIP size (bytes)"),
        default=0,
    )
    validated_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Validated at"),
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sps_package_validations",
        verbose_name=_("Validated by"),
    )
    status = models.CharField(
        max_length=16,
        choices=SPSPackageValidationStatus.choices,
        default=SPSPackageValidationStatus.PENDING,
        verbose_name=_("Status"),
    )
    error_message = models.TextField(
        blank=True,
        verbose_name=_("Error message"),
    )

    panels = [
        FieldPanel("package_document"),
        FieldPanel("status"),
        FieldPanel("zip_size_bytes"),
        FieldPanel("validated_by"),
        FieldPanel("validated_at"),
        FieldPanel("validation_document"),
        FieldPanel("exceptions_document"),
        FieldPanel("error_message"),
    ]

    def __str__(self):
        return self.package_document.title

    class Meta:
        verbose_name = _("SPS package validation")
        verbose_name_plural = _("SPS package validations")
