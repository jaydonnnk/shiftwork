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


class RotationUnavailable(ShiftworkDomainError):
    """An enabled family has no never-exposed variant left (program design S7.1).

    Fail-closed: the whole run is refused and no reservation row is written. A
    refill is the operator's explicit act; recycling or reusing an exposed
    identity would fake an unseen stimulus.
    """

    kind = "conflict"


class RotationMisconfigured(ShiftworkDomainError):
    """The drawn variants do not agree on one shared request ordinal.

    A run executes one stimulus prefix, so every family's drawn variant for that
    attempt must bind the same ordinal. A mismatch is an inventory authoring
    error, not something to resolve silently at run time.
    """

    kind = "conflict"


class TaskEnvelopeInvalid(ShiftworkDomainError):
    """A captured service response is not a valid task-aware envelope (S11).

    Raised for unparseable bytes, an unknown or extra field, a request id that
    does not match the frozen request, an unknown or duplicated task id, a
    status whose explanation code is absent when the public rules require one or
    present when they forbid one, and a claim citing evidence the response did
    not list. Whether a well-formed envelope answers the customer correctly is
    an assessment question, never a validation one.
    """

    kind = "conflict"


class MissionSpecInvalid(ShiftworkDomainError):
    """A public mission rubric is not usable as frozen task specifications.

    Fail-closed like the catalog loader: a rubric that silently lost a required
    task or an explanation code would let an incomplete answer pass, so a
    malformed mission is refused rather than partially interpreted.
    """

    kind = "conflict"


class PublicStateInvalid(ShiftworkDomainError):
    """The frozen public shop state cannot supply the records a task needs."""

    kind = "conflict"


class InvestigationIncomplete(ShiftworkDomainError):
    """Diagnostic help was requested before the learner committed a diagnosis.

    The prediction gate: cause, falsifier and public test must all be present and
    owned by this shift before any hint, diagnosis or patch proposal exists.
    Deterministic orientation is not help and never takes this path.
    """

    kind = "conflict"


class AssistGatewayUnavailable(ShiftworkDomainError):
    """The session has no configured assist gateway; no help call is made."""

    kind = "conflict"


class BootstrapBlocked(ShiftworkDomainError):
    """A diagnostic bootstrap was requested without its prerequisites.

    A legacy first-choice shift with no inherited source run may use exactly one
    public bootstrap diagnostic, and only once a safely isolated executor and a
    reviewed initial request exist. Slice 11 constructs and denies the state;
    Slice 13 supplies the safe executor that permits it.
    """

    kind = "conflict"
