"""The daily-notify cron job wiring.

Regression guards for two bugs:
  * the job ran in a thread with no event loop, so the coroutine was never
    awaited (RuntimeError) — the job func must be a coroutine function;
  * the trigger fired in UTC instead of the household's timezone.
"""
from datetime import date
from inspect import iscoroutinefunction

from chore_tracker.config import AppConfig
from chore_tracker.main import _daily_notify, _reschedule, scheduler


def test_daily_job_func_is_a_coroutine():
    # AsyncIOScheduler awaits coroutine functions on the loop; a plain function
    # would be dispatched to a thread executor (the original bug).
    assert iscoroutinefunction(_daily_notify)


def test_reschedule_registers_job_in_configured_timezone():
    cfg = AppConfig(start_date=date(2026, 1, 1), notify_times=["08:00"], timezone="America/Denver")
    _reschedule(cfg)
    jobs = scheduler.get_jobs()
    assert len(jobs) == 1
    job = jobs[0]
    assert iscoroutinefunction(job.func)
    assert "America/Denver" in str(job.trigger.timezone)


def test_reschedule_registers_one_job_per_time():
    cfg = AppConfig(start_date=date(2026, 1, 1), notify_times=["08:00", "10:00", "17:00"])
    _reschedule(cfg)
    ids = sorted(job.id for job in scheduler.get_jobs())
    assert ids == ["daily_notify_0800", "daily_notify_1000", "daily_notify_1700"]
