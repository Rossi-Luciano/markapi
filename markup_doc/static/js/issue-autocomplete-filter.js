(function () {
  function parseAutocompleteValue(value) {
    if (!value || value === "null") {
      return null;
    }

    try {
      return JSON.parse(value);
    } catch (error) {
      return null;
    }
  }

  function getSelectedJournalId() {
    var journalInput = document.querySelector('[name="journal"]');
    var value = parseAutocompleteValue(journalInput && journalInput.value);
    return value && value.pk ? value.pk : null;
  }

  function getIssueInput() {
    return document.querySelector('[name="issue"]');
  }

  function isArticleDocxMarkupForm() {
    return Boolean(document.querySelector('[name="journal"]') && getIssueInput());
  }

  function getBodyValue(body, key) {
    if (body instanceof FormData || body instanceof URLSearchParams) {
      return body.get(key);
    }

    return null;
  }

  function setBodyValue(body, key, value) {
    if (body instanceof FormData || body instanceof URLSearchParams) {
      body.set(key, value);
    }
  }

  function isIssueAutocompleteRequest(body) {
    return getBodyValue(body, "type") === "markup_doc.Issue";
  }

  function addJournalIdToIssueRequest(body) {
    if (!isArticleDocxMarkupForm() || !isIssueAutocompleteRequest(body)) {
      return;
    }

    setBodyValue(body, "article_docx_markup_issue_filter", "1");

    var journalId = getSelectedJournalId();
    if (journalId) {
      setBodyValue(body, "journal_id", journalId);
    }
  }

  function clearIssueSelection() {
    var issueInput = getIssueInput();
    if (!issueInput || !issueInput.value || issueInput.value === "null") {
      return;
    }

    issueInput.value = "";
    issueInput.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function watchJournalChanges() {
    if (!isArticleDocxMarkupForm()) {
      return;
    }

    var lastJournalId = getSelectedJournalId();

    window.setInterval(function () {
      var currentJournalId = getSelectedJournalId();
      if (currentJournalId !== lastJournalId) {
        lastJournalId = currentJournalId;
        clearIssueSelection();
      }
    }, 500);
  }

  var originalSend = XMLHttpRequest.prototype.send;

  XMLHttpRequest.prototype.send = function (body) {
    addJournalIdToIssueRequest(body);

    return originalSend.call(this, body);
  };

  if (window.fetch) {
    var originalFetch = window.fetch;

    window.fetch = function (resource, options) {
      if (options && options.body) {
        addJournalIdToIssueRequest(options.body);
      }

      return originalFetch.call(this, resource, options);
    };
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", watchJournalChanges);
  } else {
    watchJournalChanges();
  }
})();
