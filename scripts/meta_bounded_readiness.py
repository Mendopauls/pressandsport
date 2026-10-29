#!/usr/bin/env python3
"""Bounded Meta container readiness polling; GET status only.

Does not create containers, publish media, or write to the database.
Unknown/error/published statuses fail closed; no POST retries.
"""
from scripts.meta_container_status import classify_container_status, validate_container_id

class ContainerNotReady(RuntimeError):
    pass

def wait_until_ready(meta, container_id, *, max_checks=6, interval_seconds=2, sleep=None):
    validate_container_id(container_id)
    if not isinstance(max_checks, int) or isinstance(max_checks, bool) or not 1 <= max_checks <= 30:
        raise ValueError("max_checks must be between 1 and 30")
    if not isinstance(interval_seconds, (int, float)) or isinstance(interval_seconds, bool) or not 0 <= interval_seconds <= 30:
        raise ValueError("invalid polling interval")
    if sleep is None:
        from time import sleep as sleep
    for attempt in range(max_checks):
        classification = classify_container_status(container_id, meta.status(container_id))
        if classification == "ready":
            return True
        if classification != "pending":
            raise ContainerNotReady("Meta container not publishable: " + classification)
        if attempt + 1 < max_checks:
            sleep(interval_seconds)
    raise ContainerNotReady("Meta container readiness timeout; manual reconciliation required")
