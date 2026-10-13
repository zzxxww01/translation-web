"""Offline flat-rate token estimates from explicitly provided route-specific prices.

This is not an invoice calculator: missing usage/prices stay unknown; currencies
are never combined and relay prices are never guessed from upstream model names.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

_MILLION = Decimal(1_000_000)


def _price(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise ValueError("Token prices must be finite, nonnegative numbers")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Missing or invalid token price") from exc
    if not result.is_finite() or result < 0:
        raise ValueError("Token prices must be finite, nonnegative numbers")
    return result


def _count(group: dict, field: str) -> int:
    value = group.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"Missing or invalid usage counter: {field}")
    return value


def estimate_token_cost(summary: dict, rate_card: dict) -> dict:
    """Estimate only groups with complete token counts and exact provider/model rates.

    With unknown cache usage, return a range for the input-token component under
    the supplied flat rates. Missing input/output counts make the group unpriced.
    Rate effective dates/source are reported for human reconciliation; this tool
    deliberately does not infer tier thresholds, exchange rates or historical rates.
    """
    quotes = {}
    for row in rate_card.get("rates", []):
        key = (row["provider_id"], row["model"])
        if key in quotes:
            raise ValueError("Duplicate provider/model price; select one rate period explicitly")
        if not row.get("currency") or not row.get("source") or not row.get("effective_date"):
            raise ValueError("Every price requires currency, source and effective_date")
        quotes[key] = (row, _price(row.get("input_per_million")),
                       _price(row.get("cached_input_per_million")), _price(row.get("output_per_million")))
    if "llm_usage" in summary:
        summary = summary["llm_usage"]
    results, subtotals = [], {}
    groups = summary.get("groups", [])
    complete = bool(groups)
    for group in groups:
        key = (group.get("provider_id"), group.get("model"))
        item = {"provider_id": key[0], "model": key[1], "phase": group.get("phase"),
                "calls": group.get("api_calls"), "estimated_min": None, "estimated_max": None}
        if key not in quotes:
            item["status"] = "missing_price"
            complete = False
        elif group.get("unknown_input_calls", 1) or group.get("unknown_billable_output_calls", 1):
            item["status"] = "missing_usage"
            complete = False
        else:
            row, input_price, cache_price, output_price = quotes[key]
            inputs = _count(group, "input_tokens")
            outputs = _count(group, "billable_output_tokens")
            cached = _count(group, "cached_input_tokens")
            if cached > inputs:
                raise ValueError("Cached input cannot exceed total input")
            if group.get("unknown_cached_input_calls", 1):
                # Some calls have known reads. Only the remaining input is uncertain.
                low_input = cached * cache_price + (inputs - cached) * min(input_price, cache_price)
                high_input = cached * cache_price + (inputs - cached) * max(input_price, cache_price)
                item["status"] = "cache_usage_unknown"
                complete = False
            else:
                low_input = high_input = (inputs - cached) * input_price + cached * cache_price
                item["status"] = "priced_observed_tokens"
            low = (low_input + outputs * output_price) / _MILLION
            high = (high_input + outputs * output_price) / _MILLION
            item.update(currency=row["currency"], estimated_min=str(low), estimated_max=str(high),
                        price_source=row["source"], price_effective_date=row["effective_date"])
            currency_total = subtotals.setdefault(row["currency"], [Decimal(0), Decimal(0)])
            currency_total[0] += low
            currency_total[1] += high
        results.append(item)
    return {
        "run_id": summary.get("run_id"), "observed_token_pricing_complete": complete,
        "invoice_complete": False,
        "scope": "Flat-rate input/cache-read/generated-output tokens in completed observations only; ranges exclude unpriced groups",
        "excluded": ["unknown or late usage", "cache-write premiums", "cache storage", "tool charges", "tiered pricing", "relay surcharges", "tax", "currency conversion"],
        "by_currency": {currency: {"known_subtotal_min": str(values[0]), "known_subtotal_max": str(values[1])}
                        for currency, values in sorted(subtotals.items())},
        "groups": results,
    }
