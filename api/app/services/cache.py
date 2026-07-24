import hashlib
import json


def cache_key(
    doc_sha: str,
    stage: str,
    prompt_version: str,
    model: str,
    params: dict,
    upstream_keys: list[str],
) -> str:
    payload = json.dumps(
        {
            "doc": doc_sha,
            "stage": stage,
            "pv": prompt_version,
            "model": model,
            "params": params,
            "upstream": sorted(upstream_keys),
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()
