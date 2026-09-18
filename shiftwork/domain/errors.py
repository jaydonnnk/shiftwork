"""Typed error taxonomy (program design S2, domain/errors.py).

The contract/catalog/version integrity errors landed with Slice 2; Slice 4 adds
the response-validation, sealed-schema and sealed-authoring kinds. The executor,
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


class ServiceResponseInvalid(ShiftworkDomainError):
    """A structured service response cannot be validated against public records.

    Raised for an unresolvable evidence ref, an age attestation without
    evidence, evidence without an age attestation, or an attested age that does
    not equal the recomputed age of the newest cited record. Claim values
    contradicted by records are evaluator rule violations, not validation
    errors, and never take this path (customer_answer.py).
    """

    kind = "conflict"


class UnsupportedSealedSchema(ShiftworkDomainError):
    """A sealed case file declares a schema version this build does not support.

    A hard error by design: an unknown sealed format must alarm rather than be
    silently skipped, because a skipped acceptance case would fake a pass
    (program design S6 test 15).
    """

    kind = "conflict"


class InvalidSealedCase(ShiftworkDomainError):
    """A sealed case file is well-formed JSON but not a usable case.

    Raised at load time for an empty or duplicated ``request_ordinals`` list: a
    case that can never match an executed request ordinal would silently never
    score, which would fake a pass just like a skipped case.
    """

    kind = "conflict"
