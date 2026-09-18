from dataclasses import dataclass

from shiftwork.domain.models import ExecutorFailure


STOCK_BODY = b'{"action":"answer","claims":[{"kind":"stock","value":"in_stock"}],"evidence_refs":["catalog:9780441013593"],"record_age_ms":5400000}'
PRICE_BODY = b'{"action":"answer","claims":[{"kind":"price","value":1999}],"evidence_refs":["catalog:9780441013593:price"],"record_age_ms":5400000}'
TRUNCATED_BODY = b'{"action":'
NON_UTF8_BODY = b'\xff\xfe{"action":"answer"}'
FIXTURE_LOG = b"trusted fixture ready\n"


@dataclass(frozen=True)
class ConformanceCase:
    name: str
    statuses: tuple[int | None, ...]
    bodies: tuple[bytes, ...]
    errors: tuple[ExecutorFailure | None, ...]
    failure: ExecutorFailure | None
    elapsed_ms: int = 55
    deadline_s: int = 5


CASES = (
    ConformanceCase("happy_path", (200, 200), (STOCK_BODY, PRICE_BODY), (None, None), None),
    ConformanceCase(
        "port_dead", (None,), (b"",),
        (ExecutorFailure.SERVICE_UNREACHABLE,), ExecutorFailure.SERVICE_UNREACHABLE,
    ),
    ConformanceCase(
        "timeout", (200,), (b"",),
        (ExecutorFailure.REQUEST_TIMEOUT,), ExecutorFailure.REQUEST_TIMEOUT, elapsed_ms=2000, deadline_s=2,
    ),
    ConformanceCase(
        "truncated_body", (200,), (TRUNCATED_BODY,),
        (ExecutorFailure.CAPTURE_TRUNCATED,), ExecutorFailure.CAPTURE_TRUNCATED,
    ),
    ConformanceCase(
        "non_utf8_body", (200,), (NON_UTF8_BODY,),
        (ExecutorFailure.CAPTURE_NON_UTF8,), ExecutorFailure.CAPTURE_NON_UTF8,
    ),
    ConformanceCase(
        "connection_refused", (200, None), (STOCK_BODY, b""),
        (None, ExecutorFailure.SERVICE_UNREACHABLE), ExecutorFailure.SERVICE_UNREACHABLE,
    ),
    ConformanceCase("kill_mid_batch", (200,), (STOCK_BODY,), (None,), ExecutorFailure.SANDBOX_TERMINATED),
)
