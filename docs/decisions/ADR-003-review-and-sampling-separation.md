# ADR-003: Separate Review from Sampling Membership

> Status: CANONICAL
> Applies to: V2
> Last verified against commit: `bbe992e54f9fc583b312f919f32f91f43e53fb06`
> Owner: Project
> ADR Status: Accepted
> Date: 2026-09-12

## Context

A Product can have multiple Snapshots. Human review concerns the observed Snapshot, while a working sampling list needs one current Product membership with an evidentiary source. Export or removal must not erase a completed Review.

## Decision

Review is Snapshot-scoped. SamplingMembership is Product/current-list-scoped and records `source_snapshot_id`. Their repositories never mutate each other. Compound decisions are coordinated atomically by an application service. Removing Membership alone never changes Review. A new pending Snapshot remains pending even when its Product is already sampled from an older Snapshot.

Historical frozen-list item identifiers are stable text/index values under `list_id`, not mandatory foreign keys to live runtime entities.

## Consequences

`recommend_follow_up` can be reviewed while not currently sampled. Membership restoration validates the source Review in the same transaction. UI must communicate cross-Snapshot source differences.

## Rejected alternatives

- One status field for Review and Sampling.
- React sequencing independent Review and Membership mutations.
- Deleting historical meaning when current Membership is cleared.

## Related canonical docs

- [Product Requirements](../PRODUCT_REQUIREMENTS_V2.md)
- [Domain Model](../DOMAIN_MODEL_V2.md)
- [UX Specification](../UX_SPEC_V2.md)
