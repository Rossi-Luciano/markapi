from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from tracker.choices import (
    XML_DOCUMENT_CONVERSION_TO_PMC_ERROR,
    XML_DOCUMENT_CONVERSION_TO_PUBMED_ERROR,
    XML_DOCUMENT_PARSING_ERROR,
)
from tracker.models import XMLDocumentEvent
from xml_manager import exceptions
from xml_manager.models import XMLDocument, XMLDocumentPMC, XMLDocumentPubMed
from xml_manager.tasks import task_generate_pmc_file, task_generate_pubmed_file


def make_xml_document():
    upload = SimpleUploadedFile("article.xml", b"<article/>", content_type="text/xml")
    return XMLDocument.objects.create(xml_file=upload)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class TaskGeneratePubMedFileTests(TestCase):
    def setUp(self):
        self.xml_document = make_xml_document()

    def test_creates_pubmed_instance_on_success(self):
        with patch(
            "xml_manager.tasks.utils.generate_pubmed_for_xml_document",
            return_value="/app/markapi/media/xml_manager/pubmed/article.pubmed.xml",
        ):
            task_generate_pubmed_file.delay(self.xml_document.id)

        self.assertEqual(
            XMLDocumentPubMed.objects.filter(xml_document=self.xml_document).count(), 1
        )

    def test_records_event_on_parsing_error(self):
        with patch(
            "xml_manager.tasks.utils.generate_pubmed_for_xml_document",
            side_effect=exceptions.XML_File_Parsing_Error("bad xml"),
        ):
            task_generate_pubmed_file.delay(self.xml_document.id)

        event = XMLDocumentEvent.objects.get(xml_document=self.xml_document)
        self.assertEqual(event.error_type, XML_DOCUMENT_PARSING_ERROR)

    def test_records_event_on_pubmed_generation_error(self):
        with patch(
            "xml_manager.tasks.utils.generate_pubmed_for_xml_document",
            side_effect=exceptions.XML_File_PubMed_Generation_Error("boom"),
        ):
            task_generate_pubmed_file.delay(self.xml_document.id)

        event = XMLDocumentEvent.objects.get(xml_document=self.xml_document)
        self.assertEqual(event.error_type, XML_DOCUMENT_CONVERSION_TO_PUBMED_ERROR)

    def test_returns_false_for_unknown_xml_document(self):
        result = task_generate_pubmed_file.delay(999999)
        self.assertFalse(result.result)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class TaskGeneratePMCFileTests(TestCase):
    def setUp(self):
        self.xml_document = make_xml_document()

    def test_creates_pmc_instance_on_success(self):
        with patch(
            "xml_manager.tasks.utils.generate_pmc_for_xml_document",
            return_value="/app/markapi/media/xml_manager/pmc/article.pmc.xml",
        ):
            task_generate_pmc_file.delay(self.xml_document.id)

        self.assertEqual(
            XMLDocumentPMC.objects.filter(xml_document=self.xml_document).count(), 1
        )

    def test_records_event_on_parsing_error(self):
        with patch(
            "xml_manager.tasks.utils.generate_pmc_for_xml_document",
            side_effect=exceptions.XML_File_Parsing_Error("bad xml"),
        ):
            task_generate_pmc_file.delay(self.xml_document.id)

        event = XMLDocumentEvent.objects.get(xml_document=self.xml_document)
        self.assertEqual(event.error_type, XML_DOCUMENT_PARSING_ERROR)

    def test_records_event_on_pmc_generation_error(self):
        with patch(
            "xml_manager.tasks.utils.generate_pmc_for_xml_document",
            side_effect=exceptions.XML_File_PMC_Generation_Error("boom"),
        ):
            task_generate_pmc_file.delay(self.xml_document.id)

        event = XMLDocumentEvent.objects.get(xml_document=self.xml_document)
        self.assertEqual(event.error_type, XML_DOCUMENT_CONVERSION_TO_PMC_ERROR)

    def test_returns_false_for_unknown_xml_document(self):
        result = task_generate_pmc_file.delay(999999)
        self.assertFalse(result.result)
