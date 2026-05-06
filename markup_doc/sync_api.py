import logging

from django.conf import settings
from django.db import transaction

from core.utils.requester import fetch_data as fetch
from markup_doc.models import CollectionModel, CollectionValuesModel, JournalModel

logger = logging.getLogger(__name__)


def sync_collection_from_api():
    url = settings.CORE_COLLECTION_API_URL
    all_results = []

    while url:
        logger.info("Syncing collections page: %s", url)
        data = fetch(
            url, headers={"Accept": "application/json"}, json=True, timeout=(10, 60)
        )
        all_results.extend(data["results"])
        url = data["next"]

    logger.info("Deleting existing collection data before sync")
    CollectionModel.objects.all().delete()
    CollectionValuesModel.objects.all().delete()

    for item in all_results:
        acron = item.get("acron3")
        name = item.get("main_name", "").strip()
        if acron and name:
            CollectionValuesModel.objects.update_or_create(
                acron=acron, defaults={"name": name}
            )


def sync_journals_from_api():
    journals = JournalModel.objects.all()
    if journals.exists():
        journals.delete()

    obj = CollectionModel.objects.select_related("collection").first()

    acron_selected = obj.collection.acron if obj and obj.collection else None
    if not acron_selected:
        logger.warning("No collection selected; skipping journal sync")
        return

    new_journals = []

    url = settings.CORE_JOURNAL_API_URL
    while url:
        logger.info("Syncing journals page: %s", url)
        data = fetch(
            url, headers={"Accept": "application/json"}, json=True, timeout=(10, 60)
        )

        for item in data["results"]:
            title = item.get("title", None)
            short_title = item.get("short_title", None)
            acronym = item.get("acronym", None)
            pissn = item.get("official", {}).get("issn_print", None)
            eissn = item.get("official", {}).get("issn_electronic", None)
            acronym = item.get("acronym", None)
            pubname = item.get("publisher", [])
            title_in_database = item.get("title_in_database", [])
            title_nlm = None

            if title_in_database:
                for t in title_in_database:
                    if t.get("name", None) == "MEDLINE":
                        title_nlm = t.get("title", None)

            if pubname:
                pubname = pubname[0].get("name", None)

            scielo_journals = item.get("scielo_journal", [])

            # Obtener la primera colección asociada, si existe
            collection_acron = None
            issn_scielo = None
            if scielo_journals:
                collection_acron = scielo_journals[0].get("collection_acron")
                issn_scielo = scielo_journals[0].get("issn_scielo", None)

            if not title or acron_selected != collection_acron:
                continue  # Saltar si falta el título

            journal = JournalModel(
                title=title,
                short_title=short_title or None,
                title_nlm=title_nlm or None,
                acronym=acronym or None,
                issn=issn_scielo or None,
                pissn=pissn or None,
                eissn=eissn or None,
                pubname=pubname or None,
            )
            new_journals.append(journal)

        url = data.get("next")

    if new_journals:
        with transaction.atomic():
            JournalModel.objects.bulk_create(new_journals, ignore_conflicts=True)
