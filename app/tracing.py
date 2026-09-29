from __future__ import annotations

import os
from contextlib import contextmanager, nullcontext
from typing import Any

try:
    from langfuse import get_client, observe, propagate_attributes

    LANGFUSE_SDK_AVAILABLE = True
except ImportError:  # pragma: no cover - chỉ dùng khi chưa cài requirements
    LANGFUSE_SDK_AVAILABLE = False

    def observe(*args: Any, **kwargs: Any):
        def decorator(func):
            return func

        return decorator

    class _DummyClient:
        def update_current_span(self, **kwargs: Any) -> None:
            return None

        def update_current_generation(self, **kwargs: Any) -> None:
            return None

    def get_client():
        return _DummyClient()

    @contextmanager
    def propagate_attributes(**kwargs: Any):
        yield


def get_langfuse_client():
    # The lab uses short-lived workloads; send small batches promptly so traces
    # are visible without waiting for the SDK's default 512-span batch.
    os.environ.setdefault("LANGFUSE_FLUSH_AT", "1")
    os.environ.setdefault("LANGFUSE_FLUSH_INTERVAL", "1")
    return get_client()


def start_observation(client: Any, *, enabled: bool, **kwargs: Any):
    """Start a Langfuse v4 child observation when tracing is available."""
    if not enabled:
        return nullcontext()

    starter = getattr(client, "start_as_current_observation", None)
    if not callable(starter):
        return nullcontext()
    return starter(**kwargs)


def tracing_enabled() -> bool:
    return LANGFUSE_SDK_AVAILABLE and bool(
        os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
    )


def flush_langfuse(client: Any | None = None) -> bool:
    """Flush completed observations without making tracing a request failure."""
    if not tracing_enabled():
        return False

    target = client or get_langfuse_client()
    flush = getattr(target, "flush", None)
    if not callable(flush):
        return False

    try:
        flush()
    except Exception:
        return False
    return True


def shutdown_langfuse(client: Any | None = None) -> bool:
    """Flush and close the SDK worker on application shutdown."""
    if not tracing_enabled():
        return False

    target = client or get_langfuse_client()
    shutdown = getattr(target, "shutdown", None)
    if not callable(shutdown):
        return False

    try:
        shutdown()
    except Exception:
        return False
    return True
