"""Prepare for the hour and recover delayed starts without replaying older hours."""
import time
from datetime import datetime, timedelta, timezone


REPORT_HOURS_KST = (8, 11, 14, 17, 20, 23)
PREPARATION_SECONDS = 60 * 60
KST = timezone(timedelta(hours=9))


def require_report_slot(target, user_requested=False):
    """Regular editions run only at the six user-approved Korean report hours."""
    local = datetime.fromtimestamp(target, KST)
    if not user_requested and (local.hour not in REPORT_HOURS_KST or local.minute or local.second):
        raise ValueError("Regular BTP report is outside 08/11/14/17/20/23 KST")
    return target


def scheduled_target(now, event_name):
    if event_name != "schedule":
        return None
    hour = int(now) // 3600 * 3600
    # The :40/:50 preparations wait for the next hour. A delayed start or
    # the :05 recovery checks the current hour, using the same delivery key.
    return hour + 3600 if now - hour >= 40 * 60 else hour


def recovery_target(value, now):
    if len(value) != 10 or not value.isascii() or not value.isdigit():
        raise ValueError("Recovery hour must use UTC YYYYMMDDHH")
    target = int(datetime.strptime(value, "%Y%m%d%H").replace(tzinfo=timezone.utc).timestamp())
    if not 0 <= now - target < 3600:
        raise ValueError("Recovery is limited to the current hour; older reports are not replayed")
    return target


def hourly_key(target):
    return "hourly-" + datetime.fromtimestamp(target, timezone.utc).strftime("%Y%m%d%H")


def prepared_target(value, now):
    """Queue a reviewed edition up to one hour before its report slot."""
    if not isinstance(value, str) or len(value) != 10 or not value.isascii() or not value.isdigit():
        raise ValueError("Prepared hour must use UTC YYYYMMDDHH")
    target = int(datetime.strptime(value, "%Y%m%d%H").replace(tzinfo=timezone.utc).timestamp())
    if not -PREPARATION_SECONDS <= now - target < 3600:
        raise ValueError("Prepared edition is outside the current or imminent hour")
    return target


def editorial_target(now):
    """The current report hour or its one-hour preparation window; never replay."""
    hour = int(now) // 3600 * 3600
    for target in (hour, hour + 3600):
        if datetime.fromtimestamp(target, KST).hour in REPORT_HOURS_KST:
            return target
    return None


def wait_for_target(target, clock=None, sleep=None):
    clock = clock or time.time
    sleep = sleep or time.sleep
    while True:
        remaining = target - clock()
        if remaining <= 0:
            break
        sleep(min(5, remaining))
    return 0 <= clock() - target < 3600

