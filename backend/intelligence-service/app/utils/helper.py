from typing import Any, Dict, List


def compute_missing_fields(
    data: Dict[str, Any],
    *,
    ignore_keys: set[str] = {"invoice_id", "payment_id"},
    prefix: str = ""
) -> List[str]:
    """
    Recursively compute missing (None) fields in a nested dict.

    Rules:
    - Only checks explicit None values
    - Returns dot-paths (e.g. 'amount.total_ttc')
    - Ignores technical keys (IDs)
    - Deterministic, no inference
    """

    missing = []

    for key, value in data.items():
        if key in ignore_keys:
            continue

        path = f"{prefix}.{key}" if prefix else key

        if value is None:
            missing.append(path)

        elif isinstance(value, dict):
            missing.extend(
                compute_missing_fields(
                    value,
                    ignore_keys=ignore_keys,
                    prefix=path
                )
            )

        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    missing.extend(
                        compute_missing_fields(
                            item,
                            ignore_keys=ignore_keys,
                            prefix=f"{path}[{i}]"
                        )
                    )

    return missing
