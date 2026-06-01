import logging
from urllib.parse import urlencode

from django.conf import settings
from django.db.models import Q

from core.models import CoreSyncState
from core.utils.requester import fetch_data as fetch
from core.utils.sync_state import finalize_core_sync_state, track_max_from_item
from markup_doc.models import CollectionModel, CollectionValuesModel, Issue, JournalModel

logger = logging.getLogger(__name__)

ISSUE_SYNC_RESOURCE = "issue"


def _iter_api_pages(url, resource_name):
    while url:
        logger.info(f"Syncing {resource_name} page: {url}")

        data = fetch(
            url, headers={"Accept": "application/json"}, json=True, timeout=(10, 60)
        )
        yield data.get("results", [])
        url = data.get("next")


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


def _build_journal_from_api_item(item):
    title = item.get("title", None)
    short_title = item.get("short_title", None)
    acronym = item.get("acronym", None)
    pissn = item.get("official", {}).get("issn_print", None) if item.get("official", {}) else None
    eissn = item.get("official", {}).get("issn_electronic", None) if item.get("official", {}) else None
    pubname = item.get("publisher", [])
    title_in_database = item.get("title_in_database", [])
    title_nlm = None

    if title_in_database:
        for t in title_in_database:
            if t.get("name", None) == "MEDLINE":
                title_nlm = t.get("title", None)

    if pubname:
        pubname = pubname[0].get("name", None)
    else:
        pubname = None

    scielo_journals = item.get("scielo_journal", [])
    issn_scielo = None
    if scielo_journals:
        issn_scielo = scielo_journals[0].get("issn_scielo", None)

    return JournalModel(
        title=title,
        short_title=short_title,
        acronym=acronym,
        pissn=pissn,
        eissn=eissn,
        pubname=pubname,
        title_nlm=title_nlm,
        issn=issn_scielo,
    )


def build_api_url_core(domain, endpoint, params):
    url = f"{domain}{endpoint}"
    query = urlencode(params)
    return f"{url}?{query}"


def sync_journals_from_api():
    sync_state = CoreSyncState.get_for_resource(resource="journal")
    from_date_updated = sync_state.get_from_date_updated(
        settings.CORE_ISSUE_FROM_DATE_CREATED
    )
    url = build_api_url_core(
        domain=settings.CORE_API_DOMAIN,
        endpoint=settings.CORE_JOURNAL_API_ENDPOINT,
        params={
            "from_date_updated": from_date_updated
        }
    )
    synced_count = 0
    skipped_count = 0
    max_created = sync_state.last_updated_at

    for items in _iter_api_pages(url, "journals"):
        for item in items:
            journal = _build_journal_from_api_item(item)
            obj, _ = JournalModel.objects.update_or_create(
            title=journal.title,
            defaults={
                "short_title": journal.short_title,
                "title_nlm": journal.title_nlm,
                "acronym": journal.acronym,
                "issn": journal.issn,
                "pissn": journal.pissn,
                "eissn": journal.eissn,
                "pubname": journal.pubname,
            },
            )
            logger.info(f"Journal {obj} completed")
            max_created = track_max_from_item(max_created, item)
        finalize_core_sync_state(sync_state, max_created)
    logger.info(
        f"Journal sync finished. Synced={synced_count} skipped={skipped_count}"
    )


def _get_journal_from_issue_data(issue_data):
    journal_data = issue_data.get("journal") or {}
    issn_values = [
        journal_data.get("issn_print"),
        journal_data.get("issn_electronic"),
        journal_data.get("scielo_journal"),
    ]
    issn_values = [v for v in issn_values if v]

    if not issn_values:
        return None

    return (
        JournalModel.objects.filter(
            Q(pissn__in=issn_values)
            | Q(eissn__in=issn_values)
            | Q(issn__in=issn_values)
        )
        .order_by("id")
        .first()
    )

def build_issue_from_data(item):
    issue_data = {
        "number": item.get("number") or None,
        "volume": item.get("volume") or None,
        "season": item.get("season") or None,
        "year": item.get("year") or None,
        "month": item.get("month") or None,
        "supplement": item.get("supplement") or None,
    }
    return issue_data


def sync_issues_from_api():
    sync_state = CoreSyncState.get_for_resource(resource="issue")
    from_date_updated = sync_state.get_from_date_updated(
        settings.CORE_ISSUE_FROM_DATE_CREATED
    )
    url = build_api_url_core(
        domain=settings.CORE_API_DOMAIN,
        endpoint=settings.CORE_ISSUE_API_ENDPOINT,
        params={
            "from_date_updated": from_date_updated
        }
    )
    synced_count = 0
    skipped_count = 0
    max_created = sync_state.last_updated_at

    for items in _iter_api_pages(url, "issues"):
        for item in items:
            journal = _get_journal_from_issue_data(item)
            if not journal:
                skipped_count += 1
                continue
            issue_data = build_issue_from_data(item)
            issue_data.update({"journal": journal})
            Issue.objects.get_or_create(
                **issue_data,
            )
            synced_count += 1
            max_created = track_max_from_item(max_created, item)
        finalize_core_sync_state(sync_state, max_created)

    logger.info(
        f"Issue sync finished. from_date_created={from_date_updated} synced={synced_count} skipped={skipped_count}"
    )
