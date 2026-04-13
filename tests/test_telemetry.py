from __future__ import annotations

from bagfolio.telemetry import setup_telemetry


def test_setup_telemetry_returns_tracer():
    tracer = setup_telemetry(service_name="bagfolio-test", export=False)
    assert tracer is not None


def test_setup_telemetry_creates_provider():
    from opentelemetry import trace

    setup_telemetry(service_name="bagfolio-test-2", export=False)
    provider = trace.get_tracer_provider()
    assert provider is not None
