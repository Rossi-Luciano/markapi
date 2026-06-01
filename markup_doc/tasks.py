# Local application imports
# Standard library imports
import json
import logging
import re

# Third-party imports
import langid
from config import celery_app
from django.core.files.base import ContentFile
from django.utils.text import slugify
from markuplib.function_docx import functionsDocx
from model_ai.llama import LlamaInputSettings, LlamaService
from reference.config_gemini import create_prompt_reference

from markup_doc.labeling_utils import (
    MODEL_NAME_GEMINI,
    MODEL_NAME_LLAMA,
    apply_document_title_from_article_title,
    create_labeled_object2,
    create_special_content_object,
    extract_keywords,
    get_data_first_block,
    get_llm_model_name,
    process_reference,
    process_references,
    split_in_three,
)
from markup_doc.models import MarkupXML, ProcessStatus, UploadDocx
from markup_doc.sync_api import sync_issues_from_api, sync_journals_from_api
from markup_doc.xml import get_xml

logger = logging.getLogger(__name__)


def persist_article_xml(article, xml, stream_data_body=None):
    article.text_xml = xml
    if stream_data_body is not None:
        article.content_body = stream_data_body
    base_name = slugify(article.title or "article") or "article"
    article.file_xml.save(
        f"{base_name}.xml",
        ContentFile(xml.encode("utf-8")),
        save=False,
    )
    article.estatus = ProcessStatus.PROCESSED
    article.save()
    logger.info(
        "get_labels: XML gravado (%d bytes) para %r (pk=%s)",
        len(xml or ""),
        article.title,
        article.pk,
    )


def clean_labels(text):
    # Eliminar etiquetas tipo [kwd] o [sectitle], incluso si tienen espacios como [/ doctitle ]
    text = re.sub(r"\[\s*/?\s*\w+(?:\s+[^\]]+)?\s*\]", "", text)

    # Reemplazar múltiples espacios por uno solo
    text = re.sub(r"[ \t]+", " ", text)

    # Eliminar espacios antes de los signos de puntuación
    text = re.sub(r"\s+([;:,.])", r"\1", text)

    # Normalizar múltiples saltos de línea
    text = re.sub(r"\n+", "\n", text)

    # Quitar espacios al principio y final
    return text.strip()


@celery_app.task()
def task_sync_journals_from_api(
    user_id=None,
    collection_acron=None,
    issn_scielo=None,
    from_date_updated=None,
):
    sync_journals_from_api(
        collection_acron=collection_acron,
        issn_scielo=issn_scielo,
        from_date_updated=from_date_updated,
    )


@celery_app.task()
def task_sync_issues_from_api(
    user_id=None,
    issn_scielo=None,
    from_date_updated=None,
):
    sync_issues_from_api(
        issn_scielo=issn_scielo,
        from_date_updated=from_date_updated,
    )


@celery_app.task()
def get_labels(article_id, user_id):
    llm_model = get_llm_model_name()
    article_docx = UploadDocx.objects.get(pk=article_id)
    logger.info(
        "get_labels iniciado pk=%s título=%r (user_id=%s) — LLM: %s",
        article_id,
        article_docx.title,
        user_id,
        llm_model,
    )
    doc = functionsDocx.openDocx(article_docx.file.path)
    sections, content = functionsDocx().extractContent(doc, article_docx.file.path)
    article_docx_markup = article_docx
    stream_data = []
    stream_data_body = []
    stream_data_back = []
    num_ref = 0
    state = {
        "label": None,
        "label_next": None,
        "label_next_reset": None,
        "reset": False,
        "repeat": None,
        "body_trans": False,
        "body": False,
        "back": False,
        "references": False,
    }
    counts = {"numref": 0, "numtab": 0, "numfig": 0, "numeq": 0}

    next_item = None
    obj_reference = []
    llm_first_block = None

    for i, item in enumerate(content):
        if next_item:
            next_item = None
            continue

        obj = {}
        if item.get("type") in [
            "<abstract>",
            "<date-accepted>",
            "<date-received>",
            "<kwd-group>",
        ]:
            if item.get("type") == "<abstract>":
                if i + 1 < len(content):
                    obj["type"] = "paragraph"
                    obj["value"] = {
                        "label": "<abstract-title>",
                        "paragraph": item.get("text"),
                    }
                    stream_data.append(obj.copy())

                    next_item = content[i + 1]
                    obj["type"] = "paragraph_with_language"
                    obj["value"] = {
                        "label": "<abstract>",
                        "paragraph": next_item.get("text"),
                        "language": langid.classify(next_item.get("text"))[0] or None,
                    }
                    stream_data.append(obj.copy())

            elif item.get("type") == "<kwd-group>":
                keywords = extract_keywords(item.get("text"))
                obj["type"] = "paragraph"
                obj["value"] = {"label": "<kwd-title>", "paragraph": keywords["title"]}
                stream_data.append(obj.copy())

                obj["type"] = "paragraph_with_language"
                obj["value"] = {
                    "label": "<kwd-group>",
                    "paragraph": keywords["keywords"],
                    "language": langid.classify(
                        keywords["title"]
                        .replace("<italic>", "")
                        .replace("</italic>", "")
                    )[0]
                    or None,
                }
                stream_data.append(obj.copy())

            else:
                obj["type"] = "paragraph"
                obj["value"] = {
                    "label": item.get("type"),
                    "paragraph": item.get("text"),
                }
                stream_data.append(obj.copy())
            continue

        if item.get("type") == "first_block":
            llm_first_block = LlamaService(mode="prompt", temperature=0.1)
            output = None

            if get_llm_model_name() == MODEL_NAME_GEMINI:
                logger.info("get_labels: processando first_block com Gemini")
                raw_output = llm_first_block.run(
                    LlamaInputSettings.get_first_metadata(
                        clean_labels(item.get("text"))
                    )
                )
                match = re.search(r"\{.*\}", raw_output, re.DOTALL)
                if match:
                    output = json.loads(match.group(0))
                else:
                    logger.warning(
                        "get_labels: Gemini não devolveu JSON válido no first_block"
                    )

            if get_llm_model_name() == MODEL_NAME_LLAMA:
                output_author = get_data_first_block(
                    clean_labels(item.get("text")), "author", user_id
                )

                output_affiliation = get_data_first_block(
                    clean_labels(item.get("text")), "affiliation", user_id
                )

                output_doi = get_data_first_block(
                    clean_labels(item.get("text")), "doi", user_id
                )

                output_title = get_data_first_block(
                    clean_labels(item.get("text")), "title", user_id
                )

                # 1. Parsear cada salida
                doi_section = output_doi
                titles = output_title
                authors = output_author
                affiliations = output_affiliation

                # 2. Combinar en un único JSON
                output = {
                    "doi": doi_section.get("doi", ""),
                    "section": doi_section.get("section", ""),
                    "titles": titles,
                    "authors": authors,
                    "affiliations": affiliations,
                }

            if not output:
                continue

            obj["type"] = "paragraph"
            obj["value"] = {"label": "<article-id>", "paragraph": output["doi"]}
            stream_data.append(obj.copy())
            obj["value"] = {"label": "<subject>", "paragraph": output["section"]}
            stream_data.append(obj.copy())
            for i, tit in enumerate(output["titles"]):
                obj["type"] = "paragraph_with_language"
                obj["value"] = {
                    "label": "<article-title>" if i == 0 else "<trans-title>",
                    "paragraph": tit["title"],
                    "language": tit["language"],
                }
                stream_data.append(obj.copy())

            for i, auth in enumerate(output["authors"]):
                obj["type"] = "author_paragraph"
                obj["value"] = {
                    "label": "<contrib>",
                    "surname": auth["surname"],
                    "given_names": auth["name"],
                    "orcid": auth["orcid"],
                    "affid": auth["aff"],
                    "char": auth["char"],
                }
                stream_data.append(obj.copy())

            for i, aff in enumerate(output["affiliations"]):
                obj["type"] = "aff_paragraph"
                obj["value"] = {
                    "label": "<aff>",
                    "affid": aff["aff"],
                    "char": aff["char"],
                    "orgname": aff["orgname"],
                    "orgdiv2": aff["orgdiv2"],
                    "orgdiv1": aff["orgdiv1"],
                    "zipcode": aff["postal"],
                    "city": aff["city"],
                    "country": aff["name_country"],
                    "code_country": aff["code_country"],
                    "state": aff["state"],
                    "text_aff": aff["text_aff"],
                    #'original': aff['original']
                }
                stream_data.append(obj.copy())

        if item.get("type") in ["image", "table", "list", "compound"]:
            obj, counts = create_special_content_object(item, stream_data_body, counts)
            stream_data_body.append(obj)
            continue

        if item.get("text") is None or item.get("text") == "":
            state["label_next"] = (
                state["label_next_reset"] if state["reset"] else state["label_next"]
            )
            if state["back"]:
                state["back"] = False
                state["body"] = False
                state["references"] = True
        else:
            obj, result, state = create_labeled_object2(i, item, state, sections)

            if result:
                if (
                    item.get("text").lower()
                    in ["introducción", "introduction", "introdução"]
                    and state["references"]
                ):
                    state["body_trans"] = True
                    obj_trans = {
                        "type": "paragraph_with_language",
                        "value": {
                            "label": "<translate-body>",
                            "paragraph": "Translate",
                        },
                    }
                    stream_data_body.append(obj_trans)
                if state["body"]:
                    if state["references"]:
                        if state["body_trans"]:
                            stream_data_body.append(obj)
                        else:
                            stream_data.append(obj)
                    else:
                        stream_data_body.append(obj)
                elif state["back"]:
                    if state["label"] == "<sec>":
                        stream_data_back.append(obj)
                    if state["label"] == "<p>":
                        num_ref = num_ref + 1
                        # obj = {}#process_reference(num_ref, obj, user_id)
                        obj_reference.append(
                            {
                                "num_ref": num_ref,
                                "obj": obj,
                                "text": obj["value"]["paragraph"],
                            }
                        )
                    # stream_data_back.append(obj)
                else:
                    stream_data.append(obj)

    num_refs = [item["num_ref"] for item in obj_reference]

    if get_llm_model_name() == "LLAMA":
        for obj_ref in obj_reference:
            obj = process_reference(obj_ref["num_ref"], obj_ref["obj"], user_id)
            stream_data_back.append(obj)

    else:
        if llm_first_block is None:
            llm_first_block = LlamaService(mode="prompt", temperature=0.1)
        chunks = split_in_three(obj_reference)
        output = []
        logger.info(
            "get_labels: processando %d referências com Gemini (%d chunks)",
            len(obj_reference),
            len(chunks),
        )

        for chunk in chunks:
            if len(chunk) > 0:
                text_references = (
                    "\n".join([item["text"] for item in chunk])
                    .replace("<italic>", "")
                    .replace("</italic>", "")
                )
                prompt_reference = create_prompt_reference(text_references)

                result = llm_first_block.run(prompt_reference)

                match = re.search(r"\[.*\]", result, re.DOTALL)
                if match:
                    parsed = json.loads(match.group(0))
                    output.extend(parsed)  # Agrega a la lista de salida

        stream_data_back.extend(process_references(num_refs, output))

    article_docx_markup.content = stream_data
    article_docx_markup.content_body = stream_data_body
    article_docx_markup.content_back = stream_data_back
    apply_document_title_from_article_title(article_docx_markup, stream_data)
    article_docx_markup.save()

    xml, stream_data_body = get_xml(
        article_docx, stream_data, stream_data_body, stream_data_back
    )
    persist_article_xml(article_docx_markup, xml, stream_data_body)


@celery_app.task()
def update_xml(
    instance_id, instance_content, instance_content_body, instance_content_back
):
    instance = MarkupXML.objects.get(id=instance_id)
    content_head = instance_content
    content_body_dict = instance_content_body
    apply_document_title_from_article_title(instance, content_head)
    xml, stream_data_body = get_xml(
        instance, content_head, content_body_dict, instance_content_back
    )

    persist_article_xml(instance, xml, stream_data_body)
