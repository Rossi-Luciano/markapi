from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase
from lxml import etree

from markup_doc.labeling_utils import (
    StreamBlockAdapter,
    append_fragment,
    apply_document_title_from_article_title,
    article_title_from_front_content,
    article_title_from_front_stream,
    escape_angle_brackets_outside_tags,
    iter_front_blocks,
    normalize_aff_ids,
    parse_xml_fragment,
    plain_paragraph_text,
    sanitize_inline_xml_fragment,
    sanitize_table_html_fragment,
)
from markup_doc.models import ProcessStatus, UploadDocx
from markup_doc.tasks import persist_article_xml
from markup_doc.xml import get_xml


def minimal_article_stub(**overrides):
    defaults = {
        "language": "en",
        "acronym": None,
        "title_nlm": None,
        "journal_title": None,
        "short_title": None,
        "pissn": None,
        "eissn": None,
        "pubname": None,
        "artdate": None,
        "dateiso": None,
        "vol": None,
        "issue": None,
        "elocatid": None,
        "license": None,
        "content": [],
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class EscapeAngleBracketsTests(SimpleTestCase):
    def test_escapes_comparison_operator(self):
        result = escape_angle_brackets_outside_tags(
            "Values with p < 0.05 were significant"
        )
        self.assertIn("&lt;", result)
        self.assertNotIn("p < 0.05", result)

    def test_preserves_inline_tags(self):
        text = "<italic>α</italic> with p < 0.05"
        result = escape_angle_brackets_outside_tags(text)
        self.assertIn("<italic>α</italic>", result)
        self.assertIn("&lt; 0.05", result)

    def test_preserves_xref_tags(self):
        text = 'See <xref ref-type="bibr" rid="B1">Smith</xref> and p < 0.01'
        result = escape_angle_brackets_outside_tags(text)
        self.assertIn('<xref ref-type="bibr" rid="B1">', result)
        self.assertIn("&lt; 0.01", result)


class AppendFragmentTests(SimpleTestCase):
    def test_parses_paragraph_with_less_than(self):
        node = etree.Element("p")
        append_fragment(node, "Values with p < 0.05 were significant")
        xml = etree.tostring(node, encoding="unicode")
        self.assertIn("0.05", xml)
        self.assertNotIn("p < 0.05", xml)

    def test_parses_italic_inline(self):
        node = etree.Element("p")
        append_fragment(node, "<italic>significant</italic> result")
        xml = etree.tostring(node, encoding="unicode")
        self.assertIn("<italic>significant</italic>", xml)

    def test_empty_value_removes_node(self):
        parent = etree.Element("body")
        node = etree.SubElement(parent, "p")
        append_fragment(node, "")
        self.assertEqual(len(parent), 0)


class SanitizeTableHtmlTests(SimpleTestCase):
    def test_ampersand_in_cell_parses(self):
        table_html = "<table border='1'><tr><td>AT&T Corp</td></tr></table>"
        result = sanitize_table_html_fragment(table_html)
        parse_xml_fragment(result)
        self.assertIn("AT&amp;T", result)

    def test_less_than_in_cell_parses(self):
        table_html = "<table><tr><td>p < 0.05</td></tr></table>"
        result = sanitize_table_html_fragment(table_html)
        parse_xml_fragment(result)
        self.assertIn("&lt;", result)

    def test_th_cell_content_sanitized(self):
        table_html = "<table><tr><th>A & B</th></tr></table>"
        result = sanitize_table_html_fragment(table_html)
        root = parse_xml_fragment(result)
        self.assertEqual(root.tag, "table")


class SanitizeInlineXmlTests(SimpleTestCase):
    def test_list_item_with_ampersand(self):
        fragment = "<list-item><p>A & B</p></list-item>"
        result = sanitize_inline_xml_fragment(fragment)
        etree.fromstring(f"<root>{result}</root>")
        self.assertIn("&amp;", result)


class IterFrontBlocksTests(SimpleTestCase):
    def test_yields_from_stream_dicts(self):
        stream = [
            {
                "type": "paragraph_with_language",
                "value": {"label": "<article-title>", "paragraph": "T"},
            },
        ]
        blocks = list(iter_front_blocks(minimal_article_stub(), stream))
        self.assertEqual(len(blocks), 1)
        self.assertIsInstance(blocks[0], StreamBlockAdapter)
        self.assertEqual(blocks[0].block_type, "paragraph_with_language")
        self.assertEqual(blocks[0].value["label"], "<article-title>")

    def test_falls_back_to_article_content(self):
        block = StreamBlockAdapter(
            "paragraph",
            {"label": "<subject>", "paragraph": "Research"},
        )
        article = minimal_article_stub(content=[block])
        blocks = list(iter_front_blocks(article, None))
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].value["paragraph"], "Research")


class PlainParagraphTextTests(SimpleTestCase):
    def test_strips_italic_and_brackets(self):
        text = "[doctitle] <italic>My title</italic>"
        self.assertEqual(plain_paragraph_text(text), "My title")


class ArticleTitleFromFrontTests(SimpleTestCase):
    def test_extracts_article_title_block(self):
        stream_data = [
            {
                "type": "paragraph_with_language",
                "value": {
                    "label": "<article-title>",
                    "paragraph": "<italic>My Study</italic>",
                    "language": "en",
                },
            },
        ]
        self.assertEqual(article_title_from_front_stream(stream_data), "My Study")

    def test_skips_trans_title(self):
        stream_data = [
            {
                "type": "paragraph_with_language",
                "value": {
                    "label": "<trans-title>",
                    "paragraph": "Translated",
                    "language": "es",
                },
            },
            {
                "type": "paragraph_with_language",
                "value": {
                    "label": "<article-title>",
                    "paragraph": "Main title",
                    "language": "en",
                },
            },
        ]
        self.assertEqual(article_title_from_front_stream(stream_data), "Main title")

    def test_from_saved_content_blocks(self):
        article = minimal_article_stub(
            content=[
                StreamBlockAdapter(
                    "paragraph_with_language",
                    {
                        "label": "<article-title>",
                        "paragraph": "From content",
                        "language": "pt",
                    },
                ),
            ],
        )
        self.assertEqual(article_title_from_front_content(article), "From content")

    def test_apply_sets_title_when_blank(self):
        article = minimal_article_stub(title="")
        apply_document_title_from_article_title(
            article,
            [
                {
                    "type": "paragraph_with_language",
                    "value": {
                        "label": "<article-title>",
                        "paragraph": "Título do artigo",
                        "language": "pt",
                    },
                },
            ],
        )
        self.assertEqual(article.title, "Título do artigo")

    def test_apply_keeps_existing_title(self):
        article = minimal_article_stub(title="Já definido")
        apply_document_title_from_article_title(
            article,
            [
                {
                    "type": "paragraph_with_language",
                    "value": {
                        "label": "<article-title>",
                        "paragraph": "Outro",
                        "language": "pt",
                    },
                },
            ],
        )
        self.assertEqual(article.title, "Já definido")


class NormalizeAffIdsTests(SimpleTestCase):
    def test_single_int(self):
        self.assertEqual(normalize_aff_ids(2), [2])

    def test_list_from_gemini(self):
        self.assertEqual(normalize_aff_ids([1, 2]), [1, 2])

    def test_string_digit(self):
        self.assertEqual(normalize_aff_ids("3"), [3])

    def test_empty_values(self):
        self.assertEqual(normalize_aff_ids(None), [])
        self.assertEqual(normalize_aff_ids([]), [])
        self.assertEqual(normalize_aff_ids(""), [])


class GetXmlFrontTests(SimpleTestCase):
    def test_includes_article_title_from_data_front(self):
        article = minimal_article_stub()
        data_front = [
            {
                "type": "paragraph_with_language",
                "value": {
                    "label": "<article-title>",
                    "paragraph": "Effects of intervention",
                    "language": "en",
                },
            },
        ]
        xml, _ = get_xml(article, data_front, [], [])
        self.assertIn("<article-title>", xml)
        self.assertIn("Effects of intervention", xml)

    def test_body_paragraph_with_less_than(self):
        article = minimal_article_stub()
        data_body = [
            {
                "value": {
                    "label": "<p>",
                    "paragraph": "Result p < 0.05 was significant",
                },
            },
        ]
        xml, _ = get_xml(article, [], data_body, [])
        self.assertIn("0.05", xml)
        self.assertNotIn("p < 0.05", xml)

    def test_author_with_multiple_aff_ids(self):
        article = minimal_article_stub()
        data_front = [
            {
                "type": "paragraph_with_language",
                "value": {
                    "label": "<article-title>",
                    "paragraph": "Title",
                    "language": "en",
                },
            },
            {
                "type": "author_paragraph",
                "value": {
                    "label": "<contrib>",
                    "surname": "Silva",
                    "given_names": "Ana",
                    "orcid": None,
                    "affid": [1, 2],
                    "char": "*",
                },
            },
            {
                "type": "aff_paragraph",
                "value": {
                    "label": "<aff>",
                    "affid": 1,
                    "char": "*",
                    "orgname": "Universidade",
                    "orgdiv1": None,
                    "orgdiv2": None,
                    "city": None,
                    "state": None,
                    "code_country": "BR",
                    "text_aff": None,
                },
            },
        ]
        xml, _ = get_xml(article, data_front, [], [])
        self.assertIn('ref-type="aff"', xml)
        self.assertIn('rid="aff1"', xml)
        self.assertIn('rid="aff2"', xml)


class PersistArticleXmlTests(TestCase):
    def test_persists_text_xml_file_xml_and_processed_status(self):
        article = UploadDocx.objects.create(title="Artigo de teste")
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<article><front><article-meta/></front></article>"
        )
        persist_article_xml(article, xml)
        article.refresh_from_db()
        self.assertEqual(article.estatus, ProcessStatus.PROCESSED)
        self.assertIn("<article>", article.text_xml)
        self.assertTrue(article.file_xml.name.endswith(".xml"))
        self.assertTrue(article.file_xml.storage.exists(article.file_xml.name))

    def test_uses_slugified_title_for_xml_filename(self):
        article = UploadDocx.objects.create(title="Meu Artigo 2026")
        xml = "<article/>"
        persist_article_xml(article, xml)
        article.refresh_from_db()
        self.assertIn("meu-artigo-2026", article.file_xml.name)
