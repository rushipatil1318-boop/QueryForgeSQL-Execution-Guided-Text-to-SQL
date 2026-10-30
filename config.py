"""Small, explicit settings. Unknown JSON keys are errors, not silently ignored."""

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path


@dataclass(frozen=True)
class Limits:
    wall_seconds: float = 8.0
    cpu_seconds: int = 3
    process_memory_mb: int = 256
    sqlite_heap_mb: int = 64
    max_rows: int = 10000
    max_result_bytes: int = 2000000
    max_sql_chars: int = 16000
    max_ast_nodes: int = 1500

    def __post_init__(self):
        if not 0.01 <= self.wall_seconds <= 120:
            raise ValueError("wall_seconds must be between 0.01 and 120")
        for name, value in asdict(self).items():
            if name != "wall_seconds" and (type(value) is not int or value <= 0):
                raise ValueError(f"{name} must be a positive integer")
        if self.process_memory_mb < 96 or self.sqlite_heap_mb < 8:
            raise ValueError("Use at least 96 MiB process / 8 MiB SQLite memory")


@dataclass(frozen=True)
class ModelSettings:
    provider: str = "fixture"
    model: str = "fixture-not-an-llm"
    endpoint: str = "http://127.0.0.1:11434/api/chat"
    api_key_env: str = "QUERYFORGE_API_KEY"
    timeout_seconds: float = 120.0
    max_output_tokens: int = 512
    temperature: float = 0.0
    input_usd_per_million: float | None = None
    output_usd_per_million: float | None = None

    def __post_init__(self):
        if self.provider not in {"fixture", "ollama", "chat_completions"}:
            raise ValueError("provider must be fixture, ollama, or chat_completions")
        if not self.model.strip() or not 1 <= self.max_output_tokens <= 4096:
            raise ValueError("Provide a model and max_output_tokens between 1 and 4096")
        if not 1 <= self.timeout_seconds <= 600 or not 0 <= self.temperature <= 2:
            raise ValueError("Invalid model timeout or temperature")
        for price in (self.input_usd_per_million, self.output_usd_per_million):
            if price is not None and price < 0:
                raise ValueError("Token prices cannot be negative")


@dataclass(frozen=True)
class Settings:
    seed: int = 42
    max_repairs: int = 2
    schema_top_k: int = 4
    columns_per_table: int = 12
    max_prompt_chars: int = 30000
    use_evidence: bool = True
    limits: Limits = field(default_factory=Limits)
    model: ModelSettings = field(default_factory=ModelSettings)

    def __post_init__(self):
        if type(self.seed) is not int or not 0 <= self.seed <= 2147483647:
            raise ValueError("seed must fit a nonnegative signed 32-bit integer")
        if type(self.max_repairs) is not int or not 0 <= self.max_repairs <= 2:
            raise ValueError("At most TWO repair attempts are allowed")
        if self.schema_top_k < 1 or self.columns_per_table < 1:
            raise ValueError("Schema budgets must be positive")
        if self.max_prompt_chars < 1000:
            raise ValueError("max_prompt_chars must be at least 1000")


def load_settings(path: str | Path) -> Settings:
    raw = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    raw["limits"] = Limits(**raw.get("limits", {}))
    raw["model"] = ModelSettings(**raw.get("model", {}))
    return Settings(**raw)
