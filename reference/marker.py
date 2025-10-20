import logging

from model_ai.generic_llama import (
    GenericLlama,
    LlamaDisabledError,
    LlamaNotInstalledError,
    LlamaModelNotFoundError,
)
from reference.config import MESSAGES, RESPONSE_FORMAT
from tracker.models import GeneralEvent


def mark_reference(reference_text):
    try:
        reference_marker = GenericLlama(MESSAGES, RESPONSE_FORMAT)
        output = reference_marker.run(reference_text)
        for item in output.get("choices", []):
            yield item.get("message", {}).get("content", "")

    except (LlamaDisabledError, LlamaNotInstalledError, LlamaModelNotFoundError) as e:
        logging.error(f"Error marking reference: {e}")
        GeneralEvent.create(
            exception=e,
            exc_traceback=None,
            item=None,
            action="mark_reference",
            detail={"reference_text": reference_text}
        )
        if isinstance(e, LlamaModelNotFoundError):
            yield f"Llama model file not found: {str(e)}"
        else:
            yield f"Llama model is not available: {str(e)}"

    except Exception as e:
        logging.error(f"Unexpected error marking reference: {e}")
        GeneralEvent.create(
            exception=e,
            exc_traceback=None,
            item=None,
            action="mark_reference",
            detail={"reference_text": reference_text}
        )
        yield f"An unexpected error occurred: {str(e)}"


def mark_references(reference_block):
    for ref_row in reference_block.split("\n"):
        ref_row = ref_row.strip()
        if ref_row:
            choices = mark_reference(ref_row)
            yield {
                "reference": ref_row,
                "choices": list(choices)
            }

