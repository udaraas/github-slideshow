"""Playwright JS-injection-based browser walk-through recorder.

The recorder injects a small JavaScript snippet into any open Playwright
page that listens for ``click``, ``input``, and ``submit`` events.
Captured events can then be extracted and converted into a
:class:`~nextgen_test_automation.walkthrough.events.WalkthroughSession`.
"""
from __future__ import annotations

from typing import Any

from nextgen_test_automation.core.models import ElementLocator, StepAction
from nextgen_test_automation.walkthrough.events import WalkthroughEvent, WalkthroughSession


# ---------------------------------------------------------------------------
# JavaScript event-capture snippet injected into the browser page
# ---------------------------------------------------------------------------
_RECORDER_JS = """
(function () {
  if (window.__nextgen_recorder_active) return;
  window.__nextgen_recorder_active = true;
  window.__nextgen_events = [];

  function getLocator(el) {
    var css = null;
    if (el.id) {
      css = '#' + el.id;
    } else if (el.getAttribute && el.getAttribute('data-testid')) {
      css = '[data-testid="' + el.getAttribute('data-testid') + '"]';
    } else if (el.className && typeof el.className === 'string') {
      css = el.tagName.toLowerCase() + '.' + el.className.trim().split(/\\s+/)[0];
    } else {
      css = el.tagName.toLowerCase();
    }
    return {
      css: css,
      text: el.innerText ? el.innerText.trim().slice(0, 80) : null,
      aria_label: el.getAttribute ? el.getAttribute('aria-label') : null,
      xpath: null
    };
  }

  document.addEventListener('click', function (e) {
    window.__nextgen_events.push({
      action: 'click',
      locator: getLocator(e.target),
      payload: {},
      timestamp: new Date().toISOString()
    });
  }, true);

  document.addEventListener('input', function (e) {
    window.__nextgen_events.push({
      action: 'type',
      locator: getLocator(e.target),
      payload: { value: e.target.value },
      timestamp: new Date().toISOString()
    });
  }, true);

  document.addEventListener('submit', function (e) {
    window.__nextgen_events.push({
      action: 'click',
      locator: getLocator(e.target),
      payload: { form_submit: true },
      timestamp: new Date().toISOString()
    });
  }, true);
})();
"""


class BrowserRecorder:
    """Walk-through recorder backed by Playwright JS event injection.

    Typical usage::

        recorder = BrowserRecorder()
        # inject into an already-open Playwright page
        recorder.start(page)
        # ... user interacts with the page ...
        session = recorder.stop_and_build_session(page, app_name="My App")

    The recorder can also be used without a live browser by supplying a
    list of raw event dicts captured from a previous session via
    :meth:`record_from_events`.
    """

    # ------------------------------------------------------------------
    # Live browser recording
    # ------------------------------------------------------------------

    @property
    def injector_script(self) -> str:
        """The JS snippet to inject into a Playwright page."""
        return _RECORDER_JS

    def start(self, page: Any) -> None:
        """Inject the event-capture script into *page*."""
        page.evaluate(self.injector_script)

    def extract_events(self, page: Any) -> list[dict]:
        """Pull the captured raw event list from *page*."""
        return page.evaluate("() => window.__nextgen_events || []")

    def stop_and_build_session(
        self,
        page: Any,
        app_name: str,
        platform: str = "web",
        actor: str = "default",
    ) -> WalkthroughSession:
        """Extract events from *page* and return a :class:`WalkthroughSession`."""
        raw = self.extract_events(page)
        # Deduplicate rapid-fire input events (keep last value per element)
        raw = _dedupe_input_events(raw)
        return self.record_from_events(raw, app_name=app_name, platform=platform, actor=actor)

    # ------------------------------------------------------------------
    # Offline session construction
    # ------------------------------------------------------------------

    def record_from_events(
        self,
        raw_events: list[dict],
        app_name: str,
        platform: str = "web",
        actor: str = "default",
    ) -> WalkthroughSession:
        """Convert a list of raw event dicts into a :class:`WalkthroughSession`.

        This is the pure-Python path — no browser required.
        """
        session = WalkthroughSession(app_name=app_name, platform=platform, actor=actor)
        for evt in raw_events:
            action_str = evt.get("action", "click")
            try:
                action = StepAction(action_str)
            except ValueError:
                action = StepAction.CLICK

            loc_data = evt.get("locator") or {}
            locator = ElementLocator(
                css=loc_data.get("css"),
                text=loc_data.get("text"),
                aria_label=loc_data.get("aria_label"),
                xpath=loc_data.get("xpath"),
            )
            session.record(
                WalkthroughEvent(
                    action=action,
                    locator=locator,
                    payload=evt.get("payload") or {},
                )
            )
        return session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dedupe_input_events(events: list[dict]) -> list[dict]:
    """Collapse consecutive ``type`` events on the same element into one.

    When the user types in a field, every keystroke fires an ``input``
    event.  We keep only the *last* event per element (which has the
    final value) to avoid generating one step per character.
    """
    result: list[dict] = []
    for evt in events:
        if (
            evt.get("action") == "type"
            and result
            and result[-1].get("action") == "type"
            and result[-1].get("locator", {}).get("css") == evt.get("locator", {}).get("css")
        ):
            result[-1] = evt  # replace with the latest value
        else:
            result.append(evt)
    return result
