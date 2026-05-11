# Standard library imports
import re

# Local application imports
from model_ai.llama import LlamaService, LlamaInputSettings


def mark_article(text, metadata):
    if metadata == 'author':
        messages, response_format = LlamaInputSettings.get_author_config()
    elif metadata == 'affiliation':
        messages, response_format = LlamaInputSettings.get_affiliations()
    elif metadata == 'doi':
        messages, response_format = LlamaInputSettings.get_doi_and_section()
    elif metadata == 'title':
        messages, response_format = LlamaInputSettings.get_titles()
    else:
        raise ValueError(
            f"Unsupported metadata value: {metadata!r}. "
            "Expected one of: 'author', 'affiliation', 'doi', 'title'."
        )

    gll = LlamaService(messages, response_format)
    output = gll.run(text)
    output = output['choices'][0]['message']['content']
    if metadata == 'doi':
        output = re.search(r'\{.*\}', output, re.DOTALL)
    else:
        output = re.search(r'\[.*\]', output, re.DOTALL)
    if output:
        output = output.group(0)
    return output

def mark_reference(reference_text):
    messages, response_format = LlamaInputSettings.get_messages_and_response_format_for_reference(reference_text)
    reference_marker = LlamaService(messages, response_format)
    output = reference_marker.run(reference_text)

    for item in output["choices"]:
        yield item["message"]["content"]


def mark_references(reference_block):
    for ref_row in reference_block.split("\n"):
        ref_row = ref_row.strip()
        if ref_row:
            choices = mark_reference(ref_row)
            yield {
                "reference": ref_row,
                "choices": list(choices)
            }
