"""Typed error taxonomy (program design S2, domain/errors.py).

Slice 2 needs the contract/catalog/version integrity errors. The executor,
budget and rotation error kinds land with their slices (3, 7). Every error
carries a ``kind`` the HTTP layer maps to a stable status code, so no internal
detail leaks and no caller has to parse a message string.
"""


class ShiftworkDomainError(Exception):
    """Base for typed domain errors. ``kind`` is "not_found" or "conflict"."""

    kind = "conflict"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidContract(ShiftworkDomainError):
    """A submitted ContractParams is not valid for the referenced catalog."""

    kind = "conflict"


class CatalogTampered(ShiftworkDomainError):
    """A frozen catalog file no longer reproduces its pinned content hash."""

    kind = "conflict"


class CatalogNotFound(ShiftworkDomainError):
    """No immutable catalog exists for the requested slug/version."""

    kind = "not_found"


class VersionTampered(ShiftworkDomainError):
    """A stored artifact version no longer reproduces its recorded content hash."""

    kind = "conflict"
