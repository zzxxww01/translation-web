"""Print an offline, route-specific estimate without calling a model or network."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from src.llm.costing import estimate_token_cost


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("usage", type=Path, help="Run artifact with llm_usage, or a usage summary")
    parser.add_argument("--rates", type=Path, required=True, help="Your actual provider/model prices (not upstream guesses)")
    args = parser.parse_args()
    try:
        summary = json.loads(args.usage.read_text(encoding="utf-8"))
        prices = json.loads(args.rates.read_text(encoding="utf-8"))
        result = estimate_token_cost(summary, prices)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
