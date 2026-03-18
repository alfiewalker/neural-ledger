"""Feedback-driven learning engine.

This is the core of what makes Neural Ledger more than a retriever.
When the caller reports whether a set of hits helped, the engine:
  1. Updates the record's learned usefulness prior (the primary ranking signal).
  2. Strengthens or weakens inbound links (graph learning).
  3. Appends evidence to link history — never blind overwrite.
  4. Recomputes uncertainty from full evidence history.
  5. Touches the record's timestamp to reflect recent interaction.

The usefulness field is the key mechanism for making feedback visible in
rankings: it scales the initial retrieval score directly, so a negatively
reinforced record is retrievable but ranked lower even when its keyword or
semantic score is high.
"""

from __future__ import annotations

from datetime import datetime, timezone

from neural_ledger.internal.models import InternalLink
from neural_ledger.learn.confidence import compute_uncertainty
from neural_ledger.store.in_memory import InMemoryLinkStore, InMemoryRecordStore


# Evidence bounds
_EV_MAX = 1.0
_EV_MIN = 0.0

# Maximum evidence entries per link (prevents unbounded growth).
_MAX_EVIDENCE = 50

# Learning rate for link weight updates.
_LINK_LR = 0.1

# Learning rate for the per-record usefulness prior.
# Chosen so that ~3 positive feedbacks move usefulness from 1.0 to ~1.3,
# and ~3 negative feedbacks move it from 1.0 to ~0.7.
_USEFULNESS_LR = 0.1

_USEFULNESS_MAX = 2.0
_USEFULNESS_MIN = 0.05


def apply_feedback(
    record_ids: list[str],
    helped: float,
    record_store: InMemoryRecordStore,
    link_store: InMemoryLinkStore,
    reason: str | None = None,
) -> None:
    """Update usefulness, links, and timestamps for a set of record IDs.

    `helped` is in [0.0, 1.0]:
      - 1.0 → fully helpful: raise usefulness, strengthen links.
      - 0.0 → unhelpful: lower usefulness, weaken links.
      - intermediate values → proportional update.
    """
    now = datetime.now(timezone.utc)
    evidence_value = float(max(_EV_MIN, min(_EV_MAX, helped)))
    # Signed delta for link weights centred around 0.
    signed_delta = (evidence_value - 0.5) * 2.0 * _LINK_LR
    # Usefulness delta: positive when helped > 0.5, negative when < 0.5.
    usefulness_delta = (evidence_value - 0.5) * 2.0 * _USEFULNESS_LR

    for record_id in record_ids:
        record = record_store.get_record(record_id)
        if record is not None:
            # 1. Update per-record usefulness prior.
            new_usefulness = record.usefulness + usefulness_delta
            record.usefulness = max(_USEFULNESS_MIN, min(_USEFULNESS_MAX, new_usefulness))
            # 2. Touch timestamp.
            record.timestamp = now

        # 3. Update inbound links to this record.
        inbound_links = link_store.get_links_to(record_id)
        for link in inbound_links:
            _update_link(link, evidence_value, signed_delta, now)

        # 4. If no inbound links exist yet, create a self-reference link so
        #    the evidence history is preserved even for isolated records.
        if not inbound_links:
            existing_self = link_store.get_link(record_id, record_id)
            if existing_self is None:
                self_link = InternalLink(
                    source_id=record_id,
                    target_id=record_id,
                    weight=0.5,
                    timestamp=now,
                )
                link_store.add_link(self_link)
                _update_link(self_link, evidence_value, signed_delta, now)
            else:
                _update_link(existing_self, evidence_value, signed_delta, now)


def _update_link(
    link: InternalLink,
    evidence_value: float,
    signed_delta: float,
    now: datetime,
) -> None:
    """Mutate the link's weight, evidence, and uncertainty in place."""
    link.evidence.append(evidence_value)
    if len(link.evidence) > _MAX_EVIDENCE:
        link.evidence = link.evidence[-_MAX_EVIDENCE:]

    link.weight = max(0.0, min(1.0, link.weight + signed_delta))
    link.uncertainty = compute_uncertainty(link.evidence)
    link.timestamp = now
