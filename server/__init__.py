"""The operator server — the instrument for a brand-manager session.

Not a report viewer. `panel/v3_human_panel/brand_manager_sessions.md` defines a
predict-then-reveal protocol, and the property that makes it worth anything is
that the contact's prediction is captured BEFORE they see the engine's read.
This package enforces that server-side rather than trusting operator
discipline, the same way the consumer kiosk enforces its one-shot glance.

Nothing here renders a report. Reports come from `agent.read_model` +
`agent.dashboard_html` — the same two calls `render_read.py` makes — so the
guardrails cannot be lost by going around the model.
"""

from server.app import create_app

__all__ = ["create_app"]
