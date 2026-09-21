export function selectEvidence(output, checks, events) {
  if (!output) return { checks: [], events: [] };
  const linkedChecks = checks.filter(check => check.run_id === output.run_id && check.observed_ref === output.id);
  const checkIds = new Set(linkedChecks.map(check => check.id));
  return {
    checks: linkedChecks,
    events: events.filter(({ derivation: link }) => link && link.run_id === output.run_id &&
      link.request_ordinal === output.request_ordinal && link.observed_ref === output.id && checkIds.has(link.check_id)),
  };
}

export function bodyBytes(base64) {
  return Uint8Array.from(atob(base64), character => character.charCodeAt(0));
}
