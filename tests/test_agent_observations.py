from __future__ import annotations

from contextlib import contextmanager

from app import agent as agent_module


class ManagedPrompt:
    version = 7

    def compile(self, **variables: str) -> str:
        return (
            f"Feature={variables['feature']}\n"
            f"Docs={variables['docs']}\n"
            f"Question={variables['message']}"
        )


class RecordingObservation:
    def __init__(self, start_kwargs: dict) -> None:
        self.start_kwargs = start_kwargs
        self.updates: list[dict] = []

    def __enter__(self) -> "RecordingObservation":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def update(self, **kwargs) -> None:
        self.updates.append(kwargs)


class RecordingClient:
    def __init__(self) -> None:
        self.prompt = ManagedPrompt()
        self.observations: list[RecordingObservation] = []
        self.span_updates: list[dict] = []

    def get_prompt(self, name: str, **kwargs):
        return self.prompt

    def update_current_span(self, **kwargs) -> None:
        self.span_updates.append(kwargs)

    def start_as_current_observation(self, **kwargs):
        observation = RecordingObservation(kwargs)
        self.observations.append(observation)
        return observation


def test_agent_creates_safe_retrieval_and_generation_children(monkeypatch) -> None:
    client = RecordingClient()
    monkeypatch.setattr(agent_module, "get_langfuse_client", lambda: client)
    monkeypatch.setattr(agent_module, "tracing_enabled", lambda: True)

    @contextmanager
    def record_attributes(**kwargs):
        yield

    monkeypatch.setattr(agent_module, "propagate_attributes", record_attributes)

    result = agent_module.LabAgent.run.__wrapped__(
        agent_module.LabAgent(),
        user_id="student-01",
        feature="qa",
        session_id="session-01",
        message="Email student@vinuni.edu.vn and explain monitoring",
        correlation_id="req-12345678",
    )

    assert [item.start_kwargs["as_type"] for item in client.observations] == [
        "retriever",
        "generation",
    ]
    retrieval, generation = client.observations
    assert retrieval.start_kwargs["metadata"]["correlation_id"] == "req-12345678"
    assert generation.start_kwargs["metadata"]["correlation_id"] == "req-12345678"
    assert generation.start_kwargs["model"] == "claude-sonnet-4-5"
    assert generation.start_kwargs["prompt"] is client.prompt
    assert generation.start_kwargs["input"]["prompt_preview"].find(
        "student@vinuni.edu.vn"
    ) == -1

    generation_update = generation.updates[-1]
    assert generation_update["usage_details"]["input_tokens"] == result.tokens_in
    assert generation_update["usage_details"]["output_tokens"] == result.tokens_out
    assert generation_update["cost_details"]["total"] == result.cost_usd
    assert "student@vinuni.edu.vn" not in str(generation_update)
