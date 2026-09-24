"""Offline usage-summary microbenchmark. Does not call an LLM or read user data."""
import argparse
import json
import statistics
import time
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.llm.usage_metrics import LLMUsageMetrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--calls', type=int, default=5000)
    parser.add_argument('--polls', type=int, default=100)
    parser.add_argument('--rounds', type=int, default=7)
    args = parser.parse_args()
    if not all(0 < v <= 100000 for v in (args.calls, args.polls, args.rounds)):
        parser.error('counts must be between 1 and 100000')
    metrics = LLMUsageMetrics()
    metrics.start_run('synthetic-benchmark')
    for _ in range(args.calls):
        metrics.record_call(provider='synthetic', model='synthetic', phase='draft',
                            success=True, duration_seconds=.001,input_tokens=20,output_tokens=10)
    samples = []
    for _ in range(args.rounds):
        start = time.perf_counter()
        for _ in range(args.polls):
            metrics.summary(include_calls=False)
        samples.append((time.perf_counter()-start)*1000/args.polls)
    print(json.dumps({'calls':args.calls,'polls_per_round':args.polls,'rounds':args.rounds,
                      'median_ms_per_poll':statistics.median(samples),
                      'scope':'synthetic aggregation only, not translation latency'}, indent=2))


if __name__ == '__main__':
    main()
