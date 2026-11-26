"""Bounded, verified public downloads with atomic writes and retryable failures."""

import hashlib
import http.client
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path


def download_verified(url: str, destination: Path, expected_sha256: str,
                      max_bytes: int = 5000000, attempts: int = 3):
    if not url.startswith("https://"):
        raise ValueError("Dataset downloads require HTTPS")
    if destination.exists():
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        if digest != expected_sha256:
            raise ValueError("Cached download hash mismatch; move the file aside and retry")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "QueryForgeSQL/0.1"})
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = response.read(max_bytes + 1)
            if len(payload) > max_bytes:
                raise ValueError("Dataset download byte limit exceeded")
            if hashlib.sha256(payload).hexdigest() != expected_sha256:
                raise ValueError("Official pinned source hash mismatch; do not use this download")
            partial = destination.with_name(destination.name + ".part")
            partial.write_bytes(payload)
            partial.replace(destination)
            return
        except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, ssl.SSLCertVerificationError):
                raise
            if isinstance(exc, urllib.error.HTTPError) and exc.code not in {408, 429, 500, 502, 503, 504}:
                raise
            if attempt + 1 == attempts:
                raise RuntimeError("Pinned dataset download failed after three attempts; retry later or use the documented local import") from exc
            print(f"Dataset connection failed; retry {attempt + 2}/{attempts}")
            time.sleep(2 ** attempt)
