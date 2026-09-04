"""Generate dev + held-out test worlds and persist to backend/data/*.json."""
from __future__ import annotations
import json, os
from dataclasses import asdict
from nexus.generator.world import WorldGenerator
from nexus.schema import World

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


def _serialise(world: World) -> dict:
    def acc(a):
        d = asdict(a)
        d["created_at"] = a.created_at.isoformat()
        d["population"] = a.population.value
        d["lookalike_kind"] = a.lookalike_kind.value if a.lookalike_kind else None
        return d
    def txn(t):
        d = asdict(t)
        d["created_at"] = t.created_at.isoformat()
        d["population"] = t.population.value
        return d
    return {
        "meta": world.summary(),
        "accounts": [acc(a) for a in world.accounts],
        "transactions": [txn(t) for t in world.transactions],
    }


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    # Dev world (seed 42) and a DIFFERENT held-out test world (seed 7).
    dev = WorldGenerator(seed=42).generate(split="dev")
    test = WorldGenerator(seed=7).generate(split="test")
    for name, w in [("world_dev", dev), ("world_test", test)]:
        path = os.path.join(DATA_DIR, f"{name}.json")
        with open(path, "w") as f:
            json.dump(_serialise(w), f)
        print(f"wrote {name}.json")
        print(json.dumps(w.summary(), indent=2))
        print("-" * 50)


if __name__ == "__main__":
    main()
