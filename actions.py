"""Deprecated legacy action helpers.

This module is kept as a thin shim for backward compatibility with older
imports. Please migrate to using the packaged dispatcher:

    from canvas_agent.action_dispatcher import CanvasActionDispatcher

All logic now lives inside the `canvas_agent` package.
"""

from typing import Any, Dict  # noqa: F401

def dispatch_action(*args, **kwargs):  # noqa: D401
    """Deprecated; no-op shim. Use CanvasActionDispatcher instead."""
    return None

def perform_action(*args, **kwargs):  # noqa: D401
    """Deprecated; no-op shim. Use CanvasActionDispatcher instead."""
    return "Legacy actions module removed; use CanvasActionDispatcher."
