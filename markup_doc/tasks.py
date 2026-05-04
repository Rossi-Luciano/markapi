# Local application imports
from config import celery_app

# Standard library imports
import json
import re

from markup_doc.models import UploadDocx
from markup_doc.labeling_utils import (
    split_in_three,
    process_reference,
    process_references,
    create_labeled_object2,
    get_llm_model_name
)

from markup_doc.models import ProcessStatus
from markup_doc.labeling_utils import MODEL_NAME_GEMINI, MODEL_NAME_LLAMA
from markuplib.function_docx import functionsDocx
from model_ai.llama import LlamaService
from reference.config_gemini import create_prompt_reference
from markup_doc.sync_api import sync_journals_from_api


@celery_app.task()
def task_sync_journals_from_api():
    sync_journals_from_api()


@celery_app.task()
def get_labels(title, user_id):
    article_docx = UploadDocx.objects.get(title=title)
    doc = functionsDocx.openDocx(article_docx.file.path)
    sections, content = functionsDocx().extractContent(doc, article_docx.file.path)
    article_docx_markup = article_docx
    text_title = ''
    text_paragraph = ''
    stream_data = []
    stream_data_body = []
    stream_data_back = []
    num_ref=0
    state = {
        'label': None,
        'label_next': None,
        'label_next_reset': None,
        'reset': False,
        'repeat': None,
        'body_trans': False,
        'body': False,
        'back': False,
        'references': False
    }
    counts = {
        'numref': 0,
        'numtab': 0,
        'numfig': 0,
        'numeq': 0
    }

    next_item  = None
    obj_reference = []
    llama_model = False

    for i, item in enumerate(content):
        if next_item:
            next_item = None
            continue

        obj = {}

        if item.get('text') is None or item.get('text') == '':
            state['label_next'] = state['label_next_reset'] if state['reset'] else state['label_next']
            if state['back']:
                state['back'] = False
                state['body'] = False
                state['references'] = True
        else:

            obj, result, state = create_labeled_object2(i, item, state, sections)
                        
            if result:           
                if item.get('text').lower() in ['introducción', 'introduction', 'introdução'] and state['references']:
                    state['body_trans'] = True
                    obj_trans = {
                            'type': 'paragraph_with_language',
                            'value': {
                                'label': '<translate-body>',
                                'paragraph': 'Translate'
                            }
                        }
                    stream_data_body.append(obj_trans)    
                if state['body']:
                    if state['references']:
                        if state['body_trans']:
                            stream_data_body.append(obj)
                        else:
                            stream_data.append(obj)
                    else:
                        stream_data_body.append(obj)
                elif state['back']:
                    if state['label'] == '<sec>':
                        stream_data_back.append(obj)
                    if state['label'] == '<p>':
                        num_ref = num_ref + 1
                        #obj = {}#process_reference(num_ref, obj, user_id)
                        obj_reference.append({"num_ref": num_ref, "obj": obj, "text": obj['value']['paragraph'],})
                    #stream_data_back.append(obj)
                else:
                    stream_data.append(obj)
    
    num_refs = [item["num_ref"] for item in obj_reference]

    if get_llm_model_name() == 'LLAMA':
        for obj_ref in obj_reference:
            obj = process_reference(obj_ref['num_ref'], obj_ref['obj'], user_id)
            stream_data_back.append(obj)

    else:
        chunks = split_in_three(obj_reference)
        output=[]

        llm_first_block = LlamaService(mode='prompt', temperature=0.1)

        for chunk in chunks:
            if len(chunk) > 0:
                text_references = "\n".join([item["text"] for item in chunk]).replace('<italic>', '').replace('</italic>', '')
                prompt_reference = create_prompt_reference(text_references)

                result = llm_first_block.run(prompt_reference) 

                match = re.search(r'\[.*\]', result, re.DOTALL)
                if match:
                    parsed = json.loads(match.group(0))
                    output.extend(parsed)  # Agrega a la lista de salida
    
        stream_data_back.extend(process_references(num_refs, output))

    article_docx_markup.content = stream_data
    article_docx_markup.content_body = stream_data_body
    article_docx_markup.content_back = stream_data_back
    article_docx_markup.save()

    article_docx.estatus = ProcessStatus.PROCESSED
    article_docx.save()

