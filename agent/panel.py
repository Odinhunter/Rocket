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
    # rocket-2.1.0 (marketer-led composition): True for agents inside the
    # declared audience frame; False for discovery-tail agents drawn from
    # personas outside it. Legacy panels (no key) default True.
    in_declared_frame: bool = True

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
            "in_declared_frame": self.in_declared_frame,
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
            in_declared_frame=bool(data.get("in_declared_frame", True)),
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


# ---- Marketer-led composition (rocket-2.1.0) ----
#
# The declared audience (spec.demographics) is the sampling frame: it selects
# and weights which personas appear, and agents are simulated at the declared
# demographics. Disposition stays the response model. See docs/v2_1.


def _range_overlap_frac(
    lo_a: float, hi_a: float, lo_b: float, hi_b: float
) -> float:
    """Fraction of [lo_a, hi_a] that falls within [lo_b, hi_b], in [0, 1]."""
    span = hi_a - lo_a
    inter = max(0.0, min(hi_a, hi_b) - max(lo_a, lo_b))
    if span <= 0:  # degenerate point range: in-or-out
        return 1.0 if lo_b <= lo_a <= hi_b else 0.0
    return inter / span


def _gender_compatible(a: str, b: str) -> bool:
    wild = {"any", "unspecified"}
    return a in wild or b in wild or a == b


def demographic_overlap(
    persona: DemographicPoint, declared: DemographicPoint
) -> float:
    """How much of `persona` falls within the `declared` audience frame, in
    [0, 1]: gender compatibility (a hard 0/1 gate) × age-overlap × income-
    overlap. Zero when the persona is disjoint from the declared frame on any
    axis."""
    if not _gender_compatible(persona.gender, declared.gender):
        return 0.0
    age = _range_overlap_frac(
        persona.age_min, persona.age_max, declared.age_min, declared.age_max
    )
    inc = _range_overlap_frac(
        persona.income_lpa_min, persona.income_lpa_max,
        declared.income_lpa_min, declared.income_lpa_max,
    )
    return age * inc


def audience_mass(
    disposition: NamedDisposition, declared: list[DemographicPoint]
) -> float:
    """The fraction of a disposition's buyers that live inside the declared
    audience, in [0, 1] — a weighted average of each bundle's best overlap
    with any declared frame. A disposition with no bundles is demographically
    unspecified ('lives everywhere') and returns 1.0. This is the marketer-led
    weight: a disposition with more of its population in the buy gets more of
    the panel."""
    if not disposition.demographic_bundles:
        return 1.0
    wsum = sum(b.weight for b in disposition.demographic_bundles)
    if wsum <= 0:
        return 0.0
    total = 0.0
    for b in disposition.demographic_bundles:
        best = max(
            (demographic_overlap(b.point, f) for f in declared), default=0.0
        )
        total += b.weight * best
    return total / wsum


def _clip_point(
    persona: DemographicPoint, frame: DemographicPoint
) -> DemographicPoint:
    """The persona clipped to a declared frame — the slice of this persona
    that is actually in the buy. age/income intersect the frame; gender takes
    the specific side; the persona's geography/occupation/household context is
    preserved so the render stays coherent."""
    gender = persona.gender if persona.gender not in ("any", "unspecified") else frame.gender
    return DemographicPoint(
        gender=gender,
        age_min=max(persona.age_min, frame.age_min),
        age_max=min(persona.age_max, frame.age_max),
        income_lpa_min=max(persona.income_lpa_min, frame.income_lpa_min),
        income_lpa_max=min(persona.income_lpa_max, frame.income_lpa_max),
        geography=persona.geography,
        occupation_hint=persona.occupation_hint,
        household_hint=persona.household_hint,
    )


def _clipped_bundle_points(
    disposition: NamedDisposition, declared: list[DemographicPoint]
) -> tuple[list[DemographicPoint], list[float]]:
    """The (points, weights) to draw a CORE disposition's agents from: each
    overlapping bundle clipped to its best declared frame, weighted by
    bundle.weight × overlap. Falls back to the declared frames themselves
    (equal weight) when the disposition has no bundles or none overlap."""
    points: list[DemographicPoint] = []
    weights: list[float] = []
    for b in disposition.demographic_bundles:
        best_f: DemographicPoint | None = None
        best_ov = 0.0
        for f in declared:
            ov = demographic_overlap(b.point, f)
            if ov > best_ov:
                best_f, best_ov = f, ov
        if best_f is not None and best_ov > 0:
            points.append(_clip_point(b.point, best_f))
            weights.append(b.weight * best_ov)
    if not points:
        points = list(declared)
        weights = [1.0] * len(declared)
    return points, weights


def _natural_points(
    disposition: NamedDisposition, declared: list[DemographicPoint]
) -> tuple[list[DemographicPoint], list[float]]:
    """The (points, weights) for a TAIL disposition — its natural, unclipped
    demographics (it is out of the declared frame by definition)."""
    if disposition.demographic_bundles:
        return (
            [b.point for b in disposition.demographic_bundles],
            [b.weight for b in disposition.demographic_bundles],
        )
    return list(declared), [1.0] * len(declared)


def eligible_dispositions(
    spec: AudienceSpec, dispositions: list[NamedDisposition]
) -> list[tuple[NamedDisposition, float]]:
    """Dispositions with non-zero mass in the declared audience, paired with
    that mass. The marketer-led core; also the coverage-guard input."""
    out = [(d, audience_mass(d, spec.demographics)) for d in dispositions]
    return [(d, m) for d, m in out if m > 0]


def _fill_disposition_cells(
    disp: NamedDisposition,
    points: list[DemographicPoint],
    weights: list[float],
    ctxs: list[NamedContext],
    n_d: int,
) -> list[tuple[DemographicPoint, NamedDisposition, NamedContext]]:
    """Apportion n_d agents for one disposition across its demographic points
    (by weight) and contexts (uniform), both even-spread — same discipline as
    the bundled path."""
    wsum = sum(weights)
    demo_counts = _largest_remainder([w / wsum for w in weights], n_d)
    demo_seq = _even_spread(
        {str(i): demo_counts[i] for i in range(len(points))}
    )
    ctx_counts = _largest_remainder([1.0 / len(ctxs)] * len(ctxs), n_d)
    ctx_seq = _even_spread({str(i): ctx_counts[i] for i in range(len(ctxs))})
    return [
        (points[int(demo_seq[j])], disp, ctxs[int(ctx_seq[j])])
        for j in range(n_d)
    ]


def _choose_cells_marketer_led(
    spec: AudienceSpec,
    dispositions: list[NamedDisposition],
    tail_fraction: float,
) -> tuple[list[tuple[DemographicPoint, NamedDisposition, NamedContext]], list[bool]]:
    """Marketer-led cell selection. Returns (cells, in_frame_flags).

    CORE: personas with non-zero mass in the declared audience, weighted by
    that mass, simulated at the declared demographics (bundles clipped to the
    buy). TAIL (optional, off by default): personas outside the declared frame
    at their natural demographics, tagged out-of-frame for discovery — kept
    segregated from the core so the declared-audience numbers stay clean."""
    declared = spec.demographics
    ctxs = spec.context_envelope
    N = spec.panel_size

    core = eligible_dispositions(spec, dispositions)
    core_labels = {d.label for d, _ in core}
    excluded = [d for d in dispositions if d.label not in core_labels]

    n_tail = (
        int(round(N * tail_fraction))
        if (tail_fraction > 0 and excluded)
        else 0
    )
    n_core = N - n_tail

    # Degenerate: no persona lives in the declared audience. Compose all
    # dispositions at the declared demographics so the run still yields a
    # panel; the coverage guard (Phase 3) flags this loudly.
    if not core:
        core = [(d, 1.0) for d in dispositions]
        excluded = []
        n_core, n_tail = N, 0

    cells: list[tuple[DemographicPoint, NamedDisposition, NamedContext]] = []
    frame: list[bool] = []

    core_disps = [d for d, _ in core]
    core_masses = [m for _, m in core]
    msum = sum(core_masses)
    disp_counts = _largest_remainder([m / msum for m in core_masses], n_core)
    for d_idx, disp in enumerate(core_disps):
        n_d = disp_counts[d_idx]
        if n_d == 0:
            continue
        points, weights = _clipped_bundle_points(disp, declared)
        dcells = _fill_disposition_cells(disp, points, weights, ctxs, n_d)
        cells.extend(dcells)
        frame.extend([True] * len(dcells))

    if n_tail and excluded:
        tail_counts = _largest_remainder(
            [1.0 / len(excluded)] * len(excluded), n_tail
        )
        for d_idx, disp in enumerate(excluded):
            n_d = tail_counts[d_idx]
            if n_d == 0:
                continue
            points, weights = _natural_points(disp, declared)
            dcells = _fill_disposition_cells(disp, points, weights, ctxs, n_d)
            cells.extend(dcells)
            frame.extend([False] * len(dcells))

    return cells, frame


# ---- Public API ----


def build_panel(
    spec: AudienceSpec,
    dispositions: list[NamedDisposition],
    *,
    category: str,
    segment_granularity: SegmentGranularity = "disposition_chaos_band",
    seed: int = 71,
    marketer_led: bool = False,
    tail_fraction: float = 0.0,
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

    # Marketer-led: the declared audience selects/weights personas and agents
    # are simulated at the declared demographics. Otherwise the legacy paths —
    # per-disposition bundles take over when any selected disposition carries
    # them; else the uniform audience-level grid.
    if marketer_led:
        cells, frame_flags = _choose_cells_marketer_led(
            spec, dispositions, tail_fraction
        )
    elif any(d.demographic_bundles for d in dispositions):
        cells = _choose_cells_bundled(spec, dispositions)
        frame_flags = [True] * len(cells)
    else:
        cells = _choose_cells(spec, dispositions)
        frame_flags = [True] * len(cells)
    assert len(cells) == spec.panel_size, (
        f"cell selection produced {len(cells)} != panel_size {spec.panel_size}"
    )
    assert len(frame_flags) == spec.panel_size

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
        (
            cells[i][0], cells[i][1], cells[i][2],
            profile_by_label[chaos_seq[i]], frame_flags[i],
        )
        for i in range(spec.panel_size)
    ]

    # The seed controls only agent_id assignment order — distributions above
    # are fully deterministic given the spec.
    order = list(range(spec.panel_size))
    random.Random(seed).shuffle(order)

    panel: list[PanelAgent] = []
    for agent_id, slot in enumerate(order):
        demo, disp, ctx, chaos, in_frame = agents_unordered[slot]
        panel.append(
            PanelAgent(
                agent_id=agent_id,
                demographic=demo,
                disposition=disp,
                context=ctx,
                chaos=chaos,
                category=category,
                segment_granularity=segment_granularity,
                in_declared_frame=in_frame,
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
    marketer_led: bool = False,
    tail_fraction: float = 0.0,
) -> str:
    """SHA-1 of the fully resolved panel inputs — so a re-run with a changed
    audience, disposition library, category, seed, or composition mode is
    detectable on the run record. Mirrors RunConfig.compute_disposition_version."""
    h = hashlib.sha1()
    payload = {
        "spec": spec.to_dict(),
        "dispositions": [d.to_dict() for d in dispositions],
        "category": category,
        "segment_granularity": segment_granularity,
        "seed": seed,
        "marketer_led": marketer_led,
        "tail_fraction": tail_fraction,
    }
    h.update(json.dumps(payload, sort_keys=True).encode("utf-8"))
    return h.hexdigest()[:12]
