from agenttelemetry.model import RuntimeEvent


class InMemoryTraceCollector:
    """Small collector used by tests and early instrumentation experiments."""

    def __init__(self) -> None:
        self._events: list[RuntimeEvent] = []

    def record(self, event: RuntimeEvent) -> None:
        self._events.append(event)

    @property
    def events(self) -> list[RuntimeEvent]:
        return list(self._events)

