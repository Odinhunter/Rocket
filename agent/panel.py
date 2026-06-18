"""Population construction — resolve an AudienceSpec into a panel of agents.

A panel is the deterministic resolution of an AudienceSpec: demographics
x dispositions x contexts x a chaos *distribution*, sampled by stratified
allocation to match the specified distributions as closely as the panel
size allows.

Determinism: given the same AudienceSpec + dispositions + seed, build_panel
returns an identical panel (agent_id order included). The seed controls
ONLY the final agent_id shuffle — the cell counts and the chaos mix are a
deterministic function of the spec, not of the seed.

Marginal coverage: when panel_size >= grid size, every (demographic x
disposition x context) cell is populated. When panel_size < grid size (the
15-agent smoke case over a larger grid), every disposition, every context
and every demographic still appears at least once — joint-cell coverage is
sacrificed, marginal coverage is not.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass

from agent.entities import AudienceSpec
from agent.render import persona_core_hash
from agent.vectors import ChaosProfile, DemographicPoint, NamedContext, NamedDisposition

SegmentGranularity = str  # "disposition" | "disposition_chaos_band"


@dataclass
class PanelAgent:
    """One agent — a point across all four population axes."""

    agent_id: int
    demographic: DemographicPoint
    disposition: NamedDisposition
    context: NamedContext
    chaos: ChaosProfile
    category: str
    segment_granularity: SegmentGranularity = "disposition_chaos_band"

    @property
    def chaos_band(self) -> str:
        return self.chaos.label

    @property
    def disposition_label(self) -> str:
        return self.disposition.label

    @property
    def context_label(self) -> str:
        return self.context.label

    @property
    def segment_key(self) -> str:
        """The L2 fan-out key. Per-disposition collapses chaos; per-
        (disposition x chaos-band) keeps it — the granularity that gives the
        funnel projection per-chaos-band teeth."""
        if self.segment_granularity == "disposition":
            return self.disposition.label
        return f"{self.disposition.label}::{self.chaos.label}"

    @property
    def persona_core_hash(self) -> str:
        """Render-cache key for this agent's persona core (demographic +
        disposition vector + chaos vector + category + anchor). Agents that
        share a persona core share this hash and reuse the cached render."""
        return persona_core_hash(
            self.demographic,
            self.disposition.vector,
            self.chaos.vector,
            self.category,
            self.disposition.anchor,
        )

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "demographic": self.demographic.to_dict(),
            "disposition": self.disposition.to_dict(),
            "context": self.context.to_dict(),
            "chaos": self.chaos.to_dict(),
            "category": self.category,
            "segment_granularity": self.segment_granularity,
            "segment_key": self.segment_key,
            "chaos_band": self.chaos_band,
            "persona_core_hash": self.persona_core_hash,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PanelAgent":
        return cls(
            agent_id=int(data["agent_id"]),
            demographic=DemographicPoint.from_dict(data["demographic"]),
            disposition=NamedDisposition.from_dict(data["disposition"]),
            context=NamedContext.from_dict(data["context"]),
            chaos=ChaosProfile.from_dict(data["chaos"]),
            category=data["category"],
            segment_granularity=data.get(
                "segment_granularity", "disposition_chaos_band"
            ),
        )


# ---- Allocation helpers ----


def _largest_remainder(weights: list[float], total: int) -> list[int]:
    """Apportion `total` integer units across len(weights) buckets in
    proportion to `weights`, using the largest-remainder method so the
    counts sum to exactly `total`."""
    if total <= 0:
        return [0] * len(weights)
    raw = [w * total for w in weights]
    floors = [int(x) for x in raw]
    remainder = total - sum(floors)
    # Hand the leftover units to the buckets with the largest fractional parts.
    order = sorted(
        range(len(weights)), key=lambda i: (raw[i] - floors[i], i), reverse=True
    )
    for i in range(remainder):
        floors[order[i]] += 1
    return floors


def _even_spread(counts: dict[str, int]) -> list[str]:
    """Return a sequence containing each label `counts[label]` times, with
    the labels spread as evenly as possible (not blocked together). Used to
    decorrelate chaos profiles from the disposition/context cells so every
    per-(disposition x chaos-band) segment is populated."""
    total = sum(counts.values())
    if total == 0:
        return []
    labels = sorted(counts)
    acc = {label: 0.0 for label in labels}
    result: list[str] = []
    for _ in range(total):
        for label in labels:
            acc[label] += counts[label]
        # Pick the label most "owed" a slot; ties broken by stable label order.
        pick = max(labels, key=lambda label: (acc[label], -labels.index(label)))
        acc[pick] -= total
        result.append(pick)
    return result


def _base_cells(
    spec: AudienceSpec, dispositions: list[NamedDisposition]
) -> list[tuple[DemographicPoint, NamedDisposition, NamedContext]]:
    """The canonical (demographic, disposition, context) grid, in a stable
    order: disposition-major, then context, then demographic."""
    cells: list[tuple[DemographicPoint, NamedDisposition, NamedContext]] = []
    for disp in dispositions:
        for ctx in spec.context_envelope:
            for demo in spec.demographics:
                cells.append((demo, disp, ctx))
    return cells


def _choose_cells(
    spec: AudienceSpec, dispositions: list[NamedDisposition]
) -> list[tuple[DemographicPoint, NamedDisposition, NamedContext]]:
    """Choose exactly spec.panel_size base cells (with repetition).

    panel_size >= grid: every cell appears floor(N/G) times, the remainder
    spread round-robin — full joint coverage.
    panel_size < grid: a marginal-coverage pass guarantees every
    disposition / context / demographic appears at least once, then the
    remainder is padded round-robin over the grid.
    """
    grid = _base_cells(spec, dispositions)
    G = len(grid)
    N = spec.panel_size
    if G == 0:
        return []

    if N >= G:
        base, rem = divmod(N, G)
        chosen: list = []
        for i, cell in enumerate(grid):
            chosen.extend([cell] * (base + (1 if i < rem else 0)))
        return chosen

    # N < G: marginal-coverage pass first.
    demos, disps, ctxs = spec.demographics, dispositions, spec.context_envelope
    needed = max(len(demos), len(disps), len(ctxs))
    chosen = []
    for i in range(min(needed, N)):
        # As i sweeps 0..needed-1, i % len(axis) sweeps every value of each
        # axis at least once -> every marginal value appears.
        chosen.append((demos[i % len(demos)], disps[i % len(disps)], ctxs[i % len(ctxs)]))
    # Pad the remainder round-robin over the canonical grid.
    i = 0
    while len(chosen) < N:
        chosen.append(grid[i % G])
        i += 1
    return chosen


def _choose_cells_bundled(
    spec: AudienceSpec, dispositions: list[NamedDisposition]
) -> list[tuple[DemographicPoint, NamedDisposition, NamedContext]]:
    """Per-disposition demographic allocation.

    Each disposition draws its agents from its OWN `demographic_bundles`
    (weighted), so a library can encode a realistic per-disposition income
    distribution. A disposition with no bundles falls back to the audience-
    level `spec.demographics` (equal-weighted) — so a mixed library works.

    Deterministic: panel_size is split across dispositions disposition-major
    (matching the uniform path's skew), then within each disposition the
    agents are apportioned across bundles by weight and across contexts
    uniformly, both via largest-remainder + even-spread. No random draw.
    """
    N = spec.panel_size
    D = len(dispositions)
    ctxs = spec.context_envelope
    # Agents per disposition: equal share, remainder to the first-listed
    # (same disposition-major rounding the uniform grid produces).
    disp_counts = _largest_remainder([1.0 / D] * D, N)

    cells: list[tuple[DemographicPoint, NamedDisposition, NamedContext]] = []
    for d_idx, disp in enumerate(dispositions):
        n_d = disp_counts[d_idx]
        if n_d == 0:
            continue
        if disp.demographic_bundles:
            points = [b.point for b in disp.demographic_bundles]
            weights = [b.weight for b in disp.demographic_bundles]
        else:
            points = list(spec.demographics)
            weights = [1.0] * len(points)
        wsum = sum(weights)
        demo_counts = _largest_remainder([w / wsum for w in weights], n_d)
        # Even-spread the bundle draws and the contexts independently across
        # this disposition's agents, so income decorrelates from context and
        # every context still appears (marginal coverage) when n_d >= |ctx|.
        demo_seq = _even_spread(
            {str(i): demo_counts[i] for i in range(len(points))}
        )
        ctx_counts = _largest_remainder([1.0 / len(ctxs)] * len(ctxs), n_d)
        ctx_seq = _even_spread(
            {str(i): ctx_counts[i] for i in range(len(ctxs))}
        )
        for j in range(n_d):
            cells.append(
                (points[int(demo_seq[j])], disp, ctxs[int(ctx_seq[j])])
            )
    return cells


# ---- Public API ----


def build_panel(
    spec: AudienceSpec,
    dispositions: list[NamedDisposition],
    *,
    category: str,
    segment_granularity: SegmentGranularity = "disposition_chaos_band",
    seed: int = 71,
) -> list[PanelAgent]:
    """Resolve an AudienceSpec into exactly spec.panel_size PanelAgents.

    `dispositions` is the resolved NamedDisposition list matching
    spec.disposition_labels (the caller resolves it from the library) — in
    the same order as spec.disposition_labels.
    """
    spec.validate()
    if {d.label for d in dispositions} != set(spec.disposition_labels):
        raise ValueError(
            "build_panel: `dispositions` labels do not match "
            "spec.disposition_labels"
        )
    if len(dispositions) != len(spec.disposition_labels):
        raise ValueError("build_panel: `dispositions` has duplicate labels")

    # Per-disposition bundles (a realistic income distribution per
    # disposition) take over whenever any selected disposition carries them;
    # otherwise the uniform audience-level grid is used, unchanged.
    if any(d.demographic_bundles for d in dispositions):
        cells = _choose_cells_bundled(spec, dispositions)
    else:
        cells = _choose_cells(spec, dispositions)
    assert len(cells) == spec.panel_size, (
        f"cell selection produced {len(cells)} != panel_size {spec.panel_size}"
    )

    # Chaos profiles, apportioned to match the distribution as closely as the
    # panel size allows, then evenly spread so chaos does not correlate with
    # the disposition/context cells.
    cd = spec.chaos_distribution
    profiles = [p for p, _ in cd.weighted]
    weights = [w for _, w in cd.weighted]
    chaos_counts = _largest_remainder(weights, spec.panel_size)
    chaos_seq = _even_spread(
        {profiles[i].label: chaos_counts[i] for i in range(len(profiles))}
    )
    profile_by_label = {p.label: p for p in profiles}

    # Zip cells with the spread chaos sequence into the agent multiset.
    agents_unordered: list[tuple] = [
        (cells[i][0], cells[i][1], cells[i][2], profile_by_label[chaos_seq[i]])
        for i in range(spec.panel_size)
    ]

    # The seed controls only agent_id assignment order — distributions above
    # are fully deterministic given the spec.
    order = list(range(spec.panel_size))
    random.Random(seed).shuffle(order)

    panel: list[PanelAgent] = []
    for agent_id, slot in enumerate(order):
        demo, disp, ctx, chaos = agents_unordered[slot]
        panel.append(
            PanelAgent(
                agent_id=agent_id,
                demographic=demo,
                disposition=disp,
                context=ctx,
                chaos=chaos,
                category=category,
                segment_granularity=segment_granularity,
            )
        )
    panel.sort(key=lambda a: a.agent_id)
    return panel


def compute_panel_version(
    spec: AudienceSpec,
    dispositions: list[NamedDisposition],
    *,
    category: str,
    segment_granularity: SegmentGranularity,
    seed: int,
) -> str:
    """SHA-1 of the fully resolved panel inputs — so a re-run with a changed
    audience, disposition library, category or seed is detectable on the run
    record. Mirrors RunConfig.compute_disposition_version."""
    h = hashlib.sha1()
    payload = {
        "spec": spec.to_dict(),
        "dispositions": [d.to_dict() for d in dispositions],
        "category": category,
        "segment_granularity": segment_granularity,
        "seed": seed,
    }
    h.update(json.dumps(payload, sort_keys=True).encode("utf-8"))
    return h.hexdigest()[:12]
