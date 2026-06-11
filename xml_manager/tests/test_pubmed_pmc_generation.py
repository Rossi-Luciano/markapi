import os
import tempfile
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from xml_manager import exceptions
from xml_manager.utils import (
    generate_pmc_for_xml_document,
    generate_pubmed_for_xml_document,
)

XML_CONTENT = b"<article/>"


class GeneratePubMedForXMLDocumentTests(SimpleTestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.xml_file_path = os.path.join(self.tmpdir.name, "article.xml")
        with open(self.xml_file_path, "wb") as fp:
            fp.write(XML_CONTENT)

    @patch("xml_manager.utils.pipeline_pubmed")
    def test_generate_pubmed_for_xml_document_happy_path(self, mock_pipeline):
        mock_pipeline.return_value = "<pubmed/>"

        output_dir = os.path.join(self.tmpdir.name, "output")
        path_pubmed = generate_pubmed_for_xml_document(
            self.xml_file_path, output_dir, params={}
        )

        self.assertTrue(os.path.exists(path_pubmed))
        self.assertTrue(path_pubmed.endswith("article.pubmed.xml"))
        with open(path_pubmed, encoding="utf-8") as fp:
            self.assertEqual(fp.read(), "<pubmed/>")
        mock_pipeline.assert_called_once()

    @patch("xml_manager.utils.pipeline_pubmed")
    def test_generate_pubmed_for_xml_document_pipeline_error(self, mock_pipeline):
        mock_pipeline.side_effect = Exception("boom")

        output_dir = os.path.join(self.tmpdir.name, "output")
        with self.assertRaises(exceptions.XML_File_PubMed_Generation_Error):
            generate_pubmed_for_xml_document(self.xml_file_path, output_dir, params={})

    def test_generate_pubmed_for_xml_document_parsing_error(self):
        invalid_xml_path = os.path.join(self.tmpdir.name, "invalid.xml")
        with open(invalid_xml_path, "wb") as fp:
            fp.write(b"not xml")

        output_dir = os.path.join(self.tmpdir.name, "output")
        with self.assertRaises(exceptions.XML_File_Parsing_Error):
            generate_pubmed_for_xml_document(invalid_xml_path, output_dir, params={})


class GeneratePMCForXMLDocumentTests(SimpleTestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.xml_file_path = os.path.join(self.tmpdir.name, "article.xml")
        with open(self.xml_file_path, "wb") as fp:
            fp.write(XML_CONTENT)

    @patch("xml_manager.utils.pipeline_pmc")
    def test_generate_pmc_for_xml_document_happy_path(self, mock_pipeline):
        mock_pipeline.return_value = "<pmc/>"

        output_dir = os.path.join(self.tmpdir.name, "output")
        path_pmc = generate_pmc_for_xml_document(
            self.xml_file_path, output_dir, params={}
        )

        self.assertTrue(os.path.exists(path_pmc))
        self.assertTrue(path_pmc.endswith("article.pmc.xml"))
        with open(path_pmc, encoding="utf-8") as fp:
            self.assertEqual(fp.read(), "<pmc/>")
        mock_pipeline.assert_called_once()

    @patch("xml_manager.utils.pipeline_pmc")
    def test_generate_pmc_for_xml_document_pipeline_error(self, mock_pipeline):
        mock_pipeline.side_effect = Exception("boom")

        output_dir = os.path.join(self.tmpdir.name, "output")
        with self.assertRaises(exceptions.XML_File_PMC_Generation_Error):
            generate_pmc_for_xml_document(self.xml_file_path, output_dir, params={})

    def test_generate_pmc_for_xml_document_parsing_error(self):
        invalid_xml_path = os.path.join(self.tmpdir.name, "invalid.xml")
        with open(invalid_xml_path, "wb") as fp:
            fp.write(b"not xml")

        output_dir = os.path.join(self.tmpdir.name, "output")
        with self.assertRaises(exceptions.XML_File_Parsing_Error):
            generate_pmc_for_xml_document(invalid_xml_path, output_dir, params={})

    @patch("xml_manager.utils.pipeline_pmc")
    @patch("xml_manager.utils.xml_utils.get_xml_tree")
    def test_generate_pmc_for_xml_document_does_not_mutate_original_tree(
        self, mock_get_xml_tree, mock_pipeline
    ):
        original_tree = MagicMock(name="original_xml_tree")
        mock_get_xml_tree.return_value = original_tree
        mock_pipeline.return_value = "<pmc/>"

        output_dir = os.path.join(self.tmpdir.name, "output")
        generate_pmc_for_xml_document(self.xml_file_path, output_dir, params={})

        tree_passed_to_pipeline = mock_pipeline.call_args[0][0]
        # pipeline_pmc must receive a deepcopy, never the original xml_tree,
        # since pipeline_pmc mutates the tree in-place
        self.assertIsNot(tree_passed_to_pipeline, original_tree)
