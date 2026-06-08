"""Structured (logfmt-style) logging for the app.

Logs go to stdout — the right place for a container, where ``kubectl logs``
picks them up. Each line is human-readable but also machine-parseable:

    2026-06-08T08:00:00-0600 INFO chore_tracker.notifier notify.sent member=Jade room=Kitchen ok=True

Structured fields are passed through the standard ``logging`` ``extra=`` kwarg
and rendered as ``key=value`` pairs appended to the message, e.g.::

    log.info("notify.sent", extra={"member": name, "room": room, "ok": ok})
"""
import logging
import sys

# Attributes present on every LogRecord — anything *else* in the record's dict
# was supplied via ``extra=`` and is treated as a structured field.
_RESERVED = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime", "taskName"}


def _render(value: object) -> str:
    text = str(value)
    return f'"{text}"' if (" " in text or "=" in text) else text


class LogfmtFormatter(logging.Formatter):
    def formatMessage(self, record: logging.LogRecord) -> str:
        # Override formatMessage (not format) so structured fields land on the
        # message line, before any exception traceback that format() appends.
        base = super().formatMessage(record)
        fields = {
            key: val
            for key, val in record.__dict__.items()
            if key not in _RESERVED and not key.startswith("_")
        }
        if fields:
            extra = " ".join(f"{k}={_render(v)}" for k, v in fields.items())
            return f"{base} {extra}"
        return base


def configure_logging(level: int = logging.INFO) -> None:
    """Attach a stdout handler to the root logger. Idempotent.

    Safe to call after uvicorn sets up its own logging: uvicorn's default config
    leaves the root logger alone, so our handler survives and captures app +
    APScheduler logs that propagate to root.
    """
    root = logging.getLogger()
    if any(getattr(h, "_chore_handler", False) for h in root.handlers):
        return

    handler = logging.StreamHandler(sys.stdout)
    handler._chore_handler = True  # marker so we don't add it twice
    handler.setFormatter(
        LogfmtFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )
    root.addHandler(handler)
    root.setLevel(level)
    # APScheduler is chatty at INFO (job added/missed/executed); we emit our own
    # explicit job logs, so keep its noise to warnings and above.
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
