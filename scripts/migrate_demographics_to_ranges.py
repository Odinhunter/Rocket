"""One-shot migration: canonicalize on-disk DemographicPoints from the legacy
band/tier shape to rocket-2.1.0 continuous ranges.

Idempotent — DemographicPoint.from_dict dual-reads either shape, so running
this on already-migrated files is a no-op. Losslessness is guaranteed by the
from_dict/to_dict round-trip (bands map deterministically to ranges via
agent.vectors._BAND_TO_AGE_RANGE / _TIER_TO_LPA_RANGE).

Covers the tracked specs/*.json audience specs and the (gitignored) demo
entities. Run: python scripts/migrate_demographics_to_ranges.py
"""

from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.entities import AudienceSpec, DispositionLibrary, SavedAudience


def _migrate(path: str, loader) -> bool:
    before = Path(path).read_text()
    obj = loader(json.loads(before))
    obj.validate()  # ranges must be valid after conversion
    after = json.dumps(obj.to_dict(), indent=2, ensure_ascii=False) + "\n"
    # Re-load to prove losslessness before writing.
    loader(json.loads(after)).validate()
    if after == before:
        return False
    Path(path).write_text(after)
    return True


def main() -> None:
    targets: list[tuple[str, object]] = []
    for p in sorted(glob.glob("specs/*.json")):
        if "demographics" in json.loads(Path(p).read_text()):
            targets.append((p, AudienceSpec.from_dict))
    for p in sorted(glob.glob("runs/*/*/entities/library.json")):
        targets.append((p, DispositionLibrary.from_dict))
    for p in sorted(glob.glob("runs/*/*/entities/audiences/*.json")):
        targets.append((p, SavedAudience.from_dict))

    changed = 0
    for path, loader in targets:
        if _migrate(path, loader):
            changed += 1
            print(f"  migrated  {path}")
        else:
            print(f"  unchanged {path}")
    print(f"\n{changed}/{len(targets)} files migrated to continuous ranges.")


if __name__ == "__main__":
    main()
