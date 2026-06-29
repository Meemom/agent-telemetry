import json
from pathlib import Path

from agenttelemetry.model import RuntimeEvent


class JsonlTraceWriter:
    """Append runtime trace events as newline-delimited JSON."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def write(self, event: RuntimeEvent) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as trace_file:
            trace_file.write(
                json.dumps(event.model_dump(mode="json"), sort_keys=True) + "\n"
            )

    def write_many(self, events: list[RuntimeEvent]) -> None:
        for event in events:
            self.write(event)

