# Local application imports
from config import celery_app

from markup_doc.sync_api import sync_journals_from_api


@celery_app.task()
def task_sync_journals_from_api():
    sync_journals_from_api()
