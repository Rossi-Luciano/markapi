import io
import os
import zipfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone
from wagtail.documents.models import Document

from xml_manager.exceptions import SPS_Package_Validation_Error
from xml_manager.forms import SPSPackageValidationForm
from xml_manager.models import SPSPackageValidation, SPSPackageValidationStatus
from xml_manager.views import revalidate_sps_package_pk

User = get_user_model()


def make_minimal_sps_zip(xml_name="article.xml", xml_body=b"<article/>"):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(xml_name, xml_body)
    buffer.seek(0)
    return buffer.read()


def make_package_document(title="pkg.zip"):
    upload = SimpleUploadedFile(
        title,
        make_minimal_sps_zip(),
        content_type="application/zip",
    )
    document = Document(title=title)
    document.file.save(title, upload, save=True)
    return document, upload.size


class SPSPackageValidationFormTests(TestCase):
    def test_create_requires_zip(self):
        form = SPSPackageValidationForm(data={})
        self.assertFalse(form.is_valid())

    def test_rejects_non_zip_extension(self):
        upload = SimpleUploadedFile("pkg.txt", b"data", content_type="text/plain")
        form = SPSPackageValidationForm(
            files={"zip_upload": upload},
            data={},
        )
        self.assertFalse(form.is_valid())

    def test_accepts_zip_upload(self):
        upload = SimpleUploadedFile(
            "pkg.zip",
            make_minimal_sps_zip(),
            content_type="application/zip",
        )
        form = SPSPackageValidationForm(
            files={"zip_upload": upload},
            data={},
        )
        self.assertTrue(form.is_valid())


class SPSPackageValidationDeleteTests(TestCase):
    def test_delete_removes_all_wagtail_documents(self):
        package, zip_size = make_package_document()
        csv_doc = Document(title="report.validation.csv")
        csv_doc.file.save(
            "report.validation.csv",
            SimpleUploadedFile("report.validation.csv", b"a,b\n"),
            save=True,
        )
        exc_doc = Document(title="report.exceptions.json")
        exc_doc.file.save(
            "report.exceptions.json",
            SimpleUploadedFile("report.exceptions.json", b"{}"),
            save=True,
        )
        document_ids = {package.pk, csv_doc.pk, exc_doc.pk}

        validation = SPSPackageValidation.objects.create(
            package_document=package,
            validation_document=csv_doc,
            exceptions_document=exc_doc,
            zip_size_bytes=zip_size,
        )
        validation.delete()

        self.assertFalse(SPSPackageValidation.objects.filter(pk=validation.pk).exists())
        self.assertFalse(Document.objects.filter(pk__in=document_ids).exists())

    def test_delete_package_only_removes_package_document(self):
        package, zip_size = make_package_document()
        validation = SPSPackageValidation.objects.create(
            package_document=package,
            zip_size_bytes=zip_size,
        )
        package_id = package.pk

        validation.delete()

        self.assertFalse(Document.objects.filter(pk=package_id).exists())

    def test_delete_does_not_raise_recursion_error(self):
        package, zip_size = make_package_document()
        csv_doc = Document(title="report.validation.csv")
        csv_doc.file.save(
            "report.validation.csv",
            SimpleUploadedFile("report.validation.csv", b"a,b\n"),
            save=True,
        )
        exc_doc = Document(title="report.exceptions.json")
        exc_doc.file.save(
            "report.exceptions.json",
            SimpleUploadedFile("report.exceptions.json", b"{}"),
            save=True,
        )
        validation = SPSPackageValidation.objects.create(
            package_document=package,
            validation_document=csv_doc,
            exceptions_document=exc_doc,
            zip_size_bytes=zip_size,
            status=SPSPackageValidationStatus.DONE,
        )
        validation.delete()

    def test_queryset_delete_removes_linked_documents(self):
        package, zip_size = make_package_document()
        csv_doc = Document(title="report.validation.csv")
        csv_doc.file.save(
            "report.validation.csv",
            SimpleUploadedFile("report.validation.csv", b"a,b\n"),
            save=True,
        )
        validation = SPSPackageValidation.objects.create(
            package_document=package,
            validation_document=csv_doc,
            zip_size_bytes=zip_size,
        )
        document_ids = {package.pk, csv_doc.pk}
        validation_pk = validation.pk

        SPSPackageValidation.objects.filter(pk=validation_pk).delete()

        self.assertFalse(SPSPackageValidation.objects.filter(pk=validation_pk).exists())
        self.assertFalse(Document.objects.filter(pk__in=document_ids).exists())


def _request_for_user(user):
    request = RequestFactory().get("/admin/xml-manager/revalidate-sps/1/")
    request.user = user
    request.session = {}
    request._messages = FallbackStorage(request)
    return request


class SPSPackageValidationRevalidateViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="staff", password="secret", is_staff=True
        )
        self.package, self.zip_size = make_package_document()
        self.validation = SPSPackageValidation.objects.create(
            package_document=self.package,
            zip_size_bytes=self.zip_size,
            status=SPSPackageValidationStatus.DONE,
            validated_by=self.user,
            validated_at=timezone.now(),
            error_message="old error",
        )

    def test_revalidate_requires_staff(self):
        request = _request_for_user(
            User.objects.create_user(username="regular", password="secret")
        )
        response = revalidate_sps_package_pk(request, pk=self.validation.pk)
        self.assertEqual(response.status_code, 302)

    def test_revalidate_returns_404_for_missing_validation(self):
        request = _request_for_user(self.user)
        with self.assertRaises(Http404):
            revalidate_sps_package_pk(request, pk=99999)

