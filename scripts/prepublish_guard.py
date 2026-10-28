#!/usr/bin/env python3
"""Fail-closed orchestration of authorization and database reservation.

No Meta API calls. The caller must independently verify Meta account identity,
commit the reservation, and only then begin an explicitly authorized publish.
"""
from scripts.check_publication_authorization import validate
from scripts.publication_reservation import reserve_publication

def prepare_reservation(connection, manifest_bytes, authorization, *, identity_verified=False, now=None):
    problems = validate(manifest_bytes, authorization, now=now)
    if not identity_verified:
        problems.append("Meta Instagram account identity not independently verified")
    if problems:
        raise PermissionError("; ".join(problems))
    return reserve_publication(connection, manifest_bytes)
