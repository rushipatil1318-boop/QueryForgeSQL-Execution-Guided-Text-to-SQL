"""Tiny HTTP adapters. Credentials never enter run logs or SQL workers."""

from dataclasses import dataclass
import json
import os
import urllib.error
import urllib.parse
import urllib.request

from .config import ModelSettings


class ModelError(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        raise ModelError("Model endpoint redirected; configure the final trusted endpoint explicitly")


def response_text(value) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ModelError("Model returned no textual SQL response")
    return value


@dataclass
class Completion:
    text: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    response_model: str | None = None
    fingerprint: str | None = None


class FixtureProvider:
    """Scripted responses ONLY for plumbing tests; this is not an LLM."""
    name = "fixture"

    def __init__(self, responses: dict[str, list[str]]):
        self.responses = responses
        self.calls = {}

    def complete(self, messages, *, question_id: str, seed: int) -> Completion:
        if question_id not in self.responses:
            raise ModelError("Fixture supports only bundled demo question IDs")
        index = self.calls.get(question_id, 0)
        self.calls[question_id] = index + 1
        sequence = self.responses[question_id]
        return Completion(sequence[min(index, len(sequence) - 1)], response_model="fixture-not-an-llm")


class HTTPProvider:
    def __init__(self, settings: ModelSettings):
        self.settings = settings
        self.name = settings.provider
        parsed = urllib.parse.urlparse(settings.endpoint)
        loopback = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if parsed.scheme != "https" and not (parsed.scheme == "http" and loopback):
            raise ValueError("Use HTTPS for remote model endpoints; HTTP is only allowed on loopback")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Do not put credentials or query parameters in model endpoints")

    def complete(self, messages, *, question_id: str, seed: int) -> Completion:
        cfg = self.settings
        headers = {"Content-Type": "application/json"}
        if cfg.provider == "ollama":
            body = {"model": cfg.model, "messages": messages, "stream": False,
                    "options": {"seed": seed, "temperature": cfg.temperature,
                                "num_predict": cfg.max_output_tokens}}
        else:
            body = {"model": cfg.model, "messages": messages, "stream": False,
                    "seed": seed, "temperature": cfg.temperature,
                    "max_tokens": cfg.max_output_tokens}
            key = os.environ.get(cfg.api_key_env)
            if key:
                headers["Authorization"] = "Bearer " + key
        request = urllib.request.Request(cfg.endpoint, data=json.dumps(body).encode("utf-8"), headers=headers)
        # Deliberately no HTTP retries: a retry could duplicate a billable model call.
        # One attempt is one logged model call. Change unsupported API options explicitly.
        try:
            # A redirect must not forward prompts or Authorization to another host.
            opener = urllib.request.build_opener(NoRedirect())
            with opener.open(request, timeout=cfg.timeout_seconds) as response:
                raw = response.read(2000001)
            if len(raw) > 2000000:
                raise ModelError("Model response exceeds byte limit")
            result = json.loads(raw)
            if cfg.provider == "ollama":
                if result.get("done") is not True or result.get("done_reason") == "length":
                    raise ModelError("Model output was incomplete; review max_output_tokens")
                return Completion(response_text(result["message"]["content"]), result.get("prompt_eval_count"),
                                  result.get("eval_count"), result.get("model"))
            choice = result["choices"][0]
            if choice.get("finish_reason") not in {"stop", None}:
                raise ModelError("Model did not finish normally; review model/output settings")
            usage = result.get("usage", {})
            return Completion(response_text(choice["message"]["content"]), usage.get("prompt_tokens"),
                              usage.get("completion_tokens"), result.get("model"),
                              result.get("system_fingerprint"))
        except urllib.error.HTTPError as exc:
            # Do not copy provider error bodies: they can contain sensitive inputs.
            raise ModelError(f"Model endpoint HTTP {exc.code}; inspect provider/model configuration") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ModelError(f"Model network failure: {type(exc).__name__}") from exc
        except (ValueError, KeyError, TypeError, IndexError) as exc:
            raise ModelError("Model endpoint returned an unexpected response format") from exc


def make_provider(settings: ModelSettings, fixtures: dict | None = None):
    if settings.provider == "fixture":
        if fixtures is None:
            raise ValueError("Fixture mode requires explicitly labelled demo responses")
        return FixtureProvider(fixtures)
    return HTTPProvider(settings)
