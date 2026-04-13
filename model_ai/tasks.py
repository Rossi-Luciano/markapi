# Standard library imports
from config import celery_app
from config.settings.base import LLAMA_MODEL_DIR

# Third party imports
from huggingface_hub import login, hf_hub_download

# Local application imports
from model_ai.models import LlamaModel, DownloadStatus


def get_model(hf_token, name_model, name_file):
    login(token=hf_token)
    local_dir = LLAMA_MODEL_DIR
    downloaded_file = hf_hub_download(repo_id=name_model, filename=name_file, local_dir=local_dir)


@celery_app.task()
def download_model(id):
    try:
        instance = LlamaModel.objects.get(id=id)
        get_model(instance.hf_token, instance.name_model, instance.name_file)
        instance.download_status = DownloadStatus.DOWNLOADED
    except Exception:
        instance.download_status = DownloadStatus.ERROR
    instance.save()
