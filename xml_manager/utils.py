import csv
import json
import os

from packtools import data_checker
from packtools.sps.formats.pdf.pipeline import docx
from packtools.sps.formats.pdf.pipeline.xml import extract_article_main_language
from packtools.sps.formats.pdf.utils import file_utils
from packtools.sps.models.article_license import ArticleLicense
from packtools.sps.pid_provider.models.journal_meta import JournalID, Publisher, Title
from packtools.sps.pid_provider.xml_sps_lib import XMLWithPre
from packtools.sps.utils import xml_utils
from packtools.sps.validation.xml_validator import get_validation_results

from xml_manager import exceptions


def validate_xml_document(xml_file_path, output_root_dir, params):
    if not os.path.exists(output_root_dir):
        os.makedirs(output_root_dir)

    base_fname, fext = os.path.splitext(os.path.basename(xml_file_path))
    path_csv = os.path.join(output_root_dir, f"{base_fname}.validation.csv")
    path_exceptions = os.path.join(output_root_dir, f"{base_fname}.exceptions.json")

    try:
        validator = data_checker.XMLDataChecker(
            path_csv, path_exceptions, xml_file_path
        )
        validator.validate(params=params, csv_per_xml=False)
    except Exception as e:
        raise exceptions.XML_File_Validation_Error(f"Error during XML validation: {e}")

    return path_csv, path_exceptions


FIELDNAMES = [
    "group",
    "title",
    "parent",
    "parent_id",
    "parent_article_type",
    "item",
    "sub_item",
    "attribute",
    "validation_type",
    "response",
    "expected_value",
    "got_value",
    "advice",
]


def _extract_journal_data(xmltree):
    try:
        license_code = None
        for lic in ArticleLicense(xmltree).licenses:
            code = lic.get("code")
            if code:
                license_code = code
                break
        return {
            "abbrev_journal_title": Title(xmltree).abbreviated_journal_title,
            "publisher_name_list": Publisher(xmltree).publishers_names,
            "nlm_journal_title": JournalID(xmltree).nlm_ta,
            "license_code": license_code,
        }
    except Exception:
        return {}


def validate_zip(zip_path: str) -> tuple[list, list]:
    rows = []
    exceptions = []
    for xml_with_pre in XMLWithPre.create(path=zip_path):
        xmltree = xml_with_pre.xmltree
        rules = {"journal_data": _extract_journal_data(xmltree)}
        for result in get_validation_results(xmltree, rules):
            if not result:
                continue
            if result.get("response") == "exception":
                exceptions.append(result)
                continue
            if result.get("response") == "OK":
                continue
            group = result.get("group", "")
            item = result.get("item") or ""
            sub_item = result.get("sub_item") or ""
            attribute = "/".join(filter(None, [item, sub_item]))
            rows.append(
                {
                    "group": group,
                    "title": result.get("title"),
                    "parent": result.get("parent"),
                    "parent_id": result.get("parent_id"),
                    "parent_article_type": result.get("parent_article_type"),
                    "item": item,
                    "sub_item": sub_item,
                    "attribute": attribute,
                    "validation_type": result.get("validation_type"),
                    "response": result.get("response"),
                    "expected_value": result.get("expected_value"),
                    "got_value": result.get("got_value"),
                    "advice": result.get("advice"),
                }
            )
    return rows, exceptions


def write_exceptions_json(exceptions: list, output_path: str) -> str:
    with open(output_path, "w", encoding="utf-8") as fp:
        if exceptions:
            fp.write(
                "\n".join(json.dumps(error, ensure_ascii=False) for error in exceptions)
            )
            fp.write("\n")
    return output_path


def write_csv(rows: list, output_csv: str) -> str:
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    return output_csv


def generate_pdf_for_xml_document(xml_file_path, output_root_dir, params):
    if not os.path.exists(output_root_dir):
        os.makedirs(output_root_dir)

    if not isinstance(params, dict):
        params = {
            "base_layout": "/app/docx_layouts/layout.docx",
            "libreoffice_binary": "libreoffice",
        }

    if "base_layout" not in params:
        params["base_layout"] = "/app/docx_layouts/layout.docx"

    try:
        xml_tree = xml_utils.get_xml_tree(xml_file_path)
    except Exception as e:
        raise exceptions.XML_File_Parsing_Error(f"Error parsing XML file: {e}")

    try:
        docx_document = docx.pipeline_docx(xml_tree, data=params)
    except Exception as e:
        raise exceptions.XML_File_DOCX_Generation_Error(
            f"Error converting XML to DOCX: {e}"
        )

    main_language = extract_article_main_language(xml_tree) or params.get(
        "main_language", "pt"
    )

    base_name = os.path.basename(xml_file_path)
    f_name, f_ext = os.path.splitext(base_name)
    path_docx = os.path.join(output_root_dir, f"{f_name}.docx")
    path_pdf = os.path.join(output_root_dir, f"{f_name}.pdf")

    docx_document.save(path_docx)

    try:
        file_utils.convert_docx_to_pdf(
            path_docx,
            libreoffice_binary=params.get("libreoffice_binary", "libreoffice"),
        )
    except Exception as e:
        raise exceptions.XML_File_PDF_Generation_Error(
            f"Error generating PDF from DOCX: {e}"
        )

    return path_pdf, path_docx, main_language


def generate_html_for_xml_document(xml_file_path, output_root_dir, config):
    if not os.path.exists(output_root_dir):
        os.makedirs(output_root_dir)

    # ToDo: Implement HTML generation logic here
    return
