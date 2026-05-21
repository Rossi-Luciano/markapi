import logging
import os
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from config import celery_app
from tracker.choices import (
    XML_DOCUMENT_CONVERSION_TO_DOCX_ERROR,
    XML_DOCUMENT_CONVERSION_TO_HTML_ERROR,
    XML_DOCUMENT_CONVERSION_TO_PDF_ERROR,
    XML_DOCUMENT_PARSING_ERROR,
    XML_DOCUMENT_UNKNOWN_ERROR,
    XML_DOCUMENT_VALIDATION_ERROR,
)
from tracker.models import XMLDocumentEvent
from xml_manager import exceptions, utils
from xml_manager.forms import SPSPackageValidationForm
from xml_manager.models import (
    SPSPackageValidation,
    SPSPackageValidationStatus,
    XMLDocument,
    XMLDocumentHTML,
    XMLDocumentPDF,
)

User = get_user_model()


def _get_user(request, username=None, user_id=None):
    try:
        return User.objects.get(pk=request.user_id)
    except AttributeError:
        if user_id:
            return User.objects.get(pk=user_id)
        if username:
            return User.objects.get(username=username)


@celery_app.task(bind=True, timelimit=-1)
def task_process_xml_document(self, xml_id, user_id=None, username=None):
    try:
        xml_document = XMLDocument.objects.get(id=xml_id)
    except XMLDocument.DoesNotExist:
        logging.error(f"XML document with ID {xml_id} does not exist.")
        return False

    logging.info(f"Processing XML file {xml_document.xml_file.name}.")
    task_validate_xml_file.delay(xml_id, user_id=user_id, username=username)
    task_generate_pdf_file.delay(xml_id, user_id=user_id, username=username)
    task_generate_html_file.delay(xml_id, user_id=user_id, username=username)

    return True


@celery_app.task(bind=True, timelimit=-1)
def task_validate_xml_file(self, xml_id, user_id=None, username=None):
    try:
        xml_document = XMLDocument.objects.get(id=xml_id)
    except XMLDocument.DoesNotExist:
        logging.error(f"XML file with ID {xml_id} does not exist.")
        return False

    user = _get_user(self.request, username=username, user_id=user_id)

    logging.info(f"Starting XML validation for XML file {xml_document.xml_file.name}.")
    params = {}

    try:
        path_csv, path_exceptions = utils.validate_xml_document(
            xml_document.xml_file.path,
            output_root_dir=os.path.join(
                settings.MEDIA_ROOT, "xml_manager", "validation"
            ),
            params=params,
        )
        xml_document.validation_file.name = os.path.relpath(
            path_csv, settings.MEDIA_ROOT
        )
        xml_document.exceptions_file.name = os.path.relpath(
            path_exceptions, settings.MEDIA_ROOT
        )
        xml_document.save()
    except exceptions.XML_File_Validation_Error as e:
        logging.error(f"Error during XML validation: {e}")
        XMLDocumentEvent.create(
            xml_document=xml_document,
            error_type=XML_DOCUMENT_VALIDATION_ERROR,
            data={},
            message=str(e),
            save=True,
        )
        return False
    except Exception as e:
        logging.error(f"Unexpected error during XML validation: {e}")
        XMLDocumentEvent.create(
            xml_document=xml_document,
            error_type=XML_DOCUMENT_UNKNOWN_ERROR,
            data={},
            message=str(e),
            save=True,
        )
        return False

    logging.info(
        f"XML validation completed successfully for {xml_document.xml_file.name}."
    )

    return True


@celery_app.task(bind=True, timelimit=-1)
def task_generate_pdf_file(
    self, xml_id, libreoffice_binary="libreoffice", user_id=None, username=None
):
    try:
        xml_document = XMLDocument.objects.get(id=xml_id)
    except XMLDocument.DoesNotExist:
        logging.error(f"XML file with ID {xml_id} does not exist.")
        return False

    user = _get_user(self.request, username=username, user_id=user_id)

    params = {
        "libreoffice_binary": libreoffice_binary,
    }

    logging.info(f"Starting PDF generation for XML file {xml_document.xml_file.name}.")
    try:
        path_pdf, path_docx, lang = utils.generate_pdf_for_xml_document(
            xml_document.xml_file.path,
            output_root_dir=os.path.join(settings.MEDIA_ROOT, "xml_manager", "pdf"),
            params=params,
        )

        pdf_instance = XMLDocumentPDF(xml_document=xml_document, language=lang)
        pdf_instance.pdf_file.name = os.path.relpath(path_pdf, settings.MEDIA_ROOT)
        pdf_instance.docx_file.name = os.path.relpath(path_docx, settings.MEDIA_ROOT)
        pdf_instance.save()

    except exceptions.XML_File_Parsing_Error as e:
        logging.error(f"Error during XML parsing: {e}")
        XMLDocumentEvent.create(
            xml_document=xml_document,
            error_type=XML_DOCUMENT_PARSING_ERROR,
            data={},
            message=str(e),
            save=True,
        )

    except exceptions.XML_File_DOCX_Generation_Error as e:
        logging.error(f"Error during XML to DOCX conversion: {e}")
        XMLDocumentEvent.create(
            xml_document=xml_document,
            error_type=XML_DOCUMENT_CONVERSION_TO_DOCX_ERROR,
            data={},
            message=str(e),
            save=True,
        )

    except exceptions.XML_File_PDF_Generation_Error as e:
        logging.error(f"Error during PDF generation: {e}")
        XMLDocumentEvent.create(
            xml_document=xml_document,
            error_type=XML_DOCUMENT_CONVERSION_TO_PDF_ERROR,
            data={},
            message=str(e),
            save=True,
        )

    except Exception as e:
        logging.error(f"Unexpected error during PDF generation: {e}")
        XMLDocumentEvent.create(
            xml_document=xml_document,
            error_type=XML_DOCUMENT_UNKNOWN_ERROR,
            data={},
            message=str(e),
            save=True,
        )
        return False

    return True


@celery_app.task(bind=True, timelimit=-1)
def task_generate_html_file(self, xml_id, user_id=None, username=None):
    try:
        xml_document = XMLDocument.objects.get(id=xml_id)
    except XMLDocument.DoesNotExist:
        logging.error(f"XML file with ID {xml_id} does not exist.")
        return False

    user = _get_user(self.request, username=username, user_id=user_id)

    logging.info(f"Starting HTML generation for XML file {xml_document.xml_file.name}.")
    try:
        path_html, lang = utils.generate_html_for_xml_document(
            xml_document.xml_file.path,
            output_root_dir=os.path.join(settings.MEDIA_ROOT, "xml_manager", "html"),
            config=settings.HTML_GENERATION_CONFIG,
        )
        html_instance = XMLDocumentHTML(xml_document=xml_document, language=lang)
        html_instance.html_file.name = os.path.relpath(path_html, settings.MEDIA_ROOT)
        html_instance.save()
    except exceptions.XML_File_Parsing_Error as e:
        logging.error(f"Error during XML parsing: {e}")
        XMLDocumentEvent.create(
            xml_document=xml_document,
            error_type=XML_DOCUMENT_PARSING_ERROR,
            data={},
            message=str(e),
            save=True,
        )
    except exceptions.XML_File_HTML_Generation_Error as e:
        logging.error(f"Error during HTML generation: {e}")
        XMLDocumentEvent.create(
            xml_document=xml_document,
            error_type=XML_DOCUMENT_CONVERSION_TO_HTML_ERROR,
            data={},
            message=str(e),
            save=True,
        )
    except Exception as e:
        logging.error(f"Unexpected error during HTML generation: {e}")
        XMLDocumentEvent.create(
            xml_document=xml_document,
            error_type=XML_DOCUMENT_UNKNOWN_ERROR,
            data={},
            message=str(e),
            save=True,
        )
        return False


@celery_app.task(bind=True)
def task_validate_sps_package(self, validation_pk):
    try:
        validation = SPSPackageValidation.objects.get(pk=validation_pk)
    except SPSPackageValidation.DoesNotExist:
        logging.error(f"SPSPackageValidation pk={validation_pk} does not exist.")
        return False

    validation.status = SPSPackageValidationStatus.RUNNING
    validation.save()

    try:
        zip_path = validation.package_document.file.path
        rows, exceptions = utils.validate_zip(zip_path)

        with tempfile.TemporaryDirectory() as tmpdir:
            base_name = os.path.splitext(validation.package_document.title)[0]
            csv_path = os.path.join(tmpdir, f"{base_name}.validation.csv")
            utils.write_csv(rows, csv_path)

            if validation.validation_document:
                validation.validation_document.delete()
                validation.validation_document = None

            validation.validation_document = (
                SPSPackageValidationForm.save_wagtail_document_from_path(
                    csv_path,
                    title=f"{base_name}.validation.csv",
                )
            )

            exceptions_path = os.path.join(tmpdir, f"{base_name}.exceptions.json")
            utils.write_exceptions_json(exceptions, exceptions_path)

            if validation.exceptions_document:
                validation.exceptions_document.delete()
                validation.exceptions_document = None

            validation.exceptions_document = (
                SPSPackageValidationForm.save_wagtail_document_from_path(
                    exceptions_path,
                    title=f"{base_name}.exceptions.json",
                )
            )

        validation.status = SPSPackageValidationStatus.DONE
        validation.validated_at = timezone.now()
        validation.error_message = ""

    except Exception as e:
        logging.error(f"Error during SPS package validation pk={validation_pk}: {e}")
        validation.status = SPSPackageValidationStatus.ERROR
        validation.error_message = str(e)

    validation.save()
    return True
