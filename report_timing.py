"""Prepare before the hour, publish once at the hour, and never send catch-up reports."""
import time


def scheduled_target(now, event_name):
    if event_name != "schedule":
        return None
    minute = int(now // 60) % 60
    if minute < 50:
        return None
    return (int(now) // 3600 + 1) * 3600


def wait_for_target(target, clock=None, sleep=None):
    clock = clock or time.time
    sleep = sleep or time.sleep
    while True:
        remaining = target - clock()
        if remaining <= 0:
            break
        sleep(min(5, remaining))
    return 0 <= clock() - target <= 20
