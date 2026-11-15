"""Opt-in OTLP tracing and explicit context propagation between workers."""

from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import wraps
import inspect
import os
from time import time_ns
from collections import deque
import threading
import uuid

from opentelemetry import context, trace


DIALOGUE_SERVICE = "dialbb-dialogue"
PROCESS_SERVICE = "dialbb-process"
_providers = {}
_provider_lock = threading.RLock()


class TracingProviders:
    """Own both service resources without replacing the application's global SDK."""

    def __init__(self, providers):
        self.providers = providers

    def shutdown(self):
        # TracerProvider cannot be registered globally again after shutdown.
        # Explicit providers also allow a later server lifespan to start cleanly.
        with _provider_lock:
            for service, provider in self.providers.items():
                try:
                    provider.shutdown()
                finally:
                    if _providers.get(service) is provider:
                        del _providers[service]


def create_tracer_provider():
    """Create one OTLP/HTTP pipeline per category at server startup.

    service.name belongs to the provider's Resource, not a span attribute or
    instrumentation scope. Both pipelines share standard OTLP exporter settings.
    SERVICE_NAME and OTEL_SERVICE_NAME never override these category names.
    """
    if os.getenv("OTEL_SDK_DISABLED", "").lower() == "true":
        return None
    enabled = os.getenv("OTEL_TRACES_ENABLED", "").lower() == "true"
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT") or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not enabled and not endpoint:
        return None

    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    with _provider_lock:
        if _providers:
            return None
        providers = {}
        try:
            for service in (DIALOGUE_SERVICE, PROCESS_SERVICE):
                provider = TracerProvider(resource=Resource.create({"service.name": service}))
                providers[service] = provider
                provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        except BaseException:
            for provider in providers.values():
                provider.shutdown()
            raise
        _providers.update(providers)
        return TracingProviders(providers)


def get_tracer(parent=None):
    """Select the library service only inside an isolated process context."""
    service = context.get_value("dialbb.service", parent) or DIALOGUE_SERVICE
    provider = _providers.get(service)
    if provider is None:
        return trace.get_tracer("dialbb")
    return provider.get_tracer("dialbb")


@contextmanager
def operation(name, attributes=None, *, parent=None, links=None):
    parent = context.get_current() if parent is None else parent
    attributes = {"thread.name": threading.current_thread().name,
                  "thread.id": threading.get_ident(),
                  **(context.get_value("dialbb.trace_attributes", parent) or {}),
                  **(attributes or {})}
    turn = current_turn(parent)
    if turn is not None:
        attributes.setdefault("turn.id", turn.turn_id)
    # Late playback/results after a completed or cancelled turn must not extend
    # the duration shown for that turn in Jaeger's trace search.
    if turn is not None and turn.finished:
        parent, turn = context.Context(), None
    token = context.attach(parent)
    span = get_tracer(parent).start_span(name, attributes=attributes, links=links)
    if turn is not None:
        turn.track_scope(span)
    try:
        with trace.use_span(span, end_on_exit=False):
            yield span
    except BaseException:
        if turn is not None and name in {
            "dialbb.request", "tts.request", "core.process_stt_event",
            "core.process_dialbb_response", "core.start_system_response",
        }:
            turn.finish("error", error=True)
        raise
    finally:
        if turn is not None:
            turn.end_scope(span)
        elif span.is_recording():
            span.end()
        if token is not None:
            context.detach(token)


def traced_process(function):
    """Always isolate library processing from server work and voice lifetimes."""
    @wraps(function)
    def wrapped(self, request, initial=False):
        blocks = getattr(self, "_trace_blocks", ())
        attributes = {
            "dialbb.trace_mode": "independent",
            "dialbb.trace_blocks": list(blocks),
            "request.initial": initial,
        }
        config_file = getattr(self, "_trace_config_file", None)
        if config_file is not None:
            attributes["dialbb.config_file"] = config_file
        caller_span = trace.get_current_span()
        caller = caller_span.get_span_context()
        turn = current_turn()
        attributes["trace.scope"] = "dialbb.process"
        if caller.is_valid:
            attributes["dialogue.trace_id"] = format(caller.trace_id, "032x")
            attributes["dialogue.span_id"] = format(caller.span_id, "016x")
        if turn is not None:
            attributes["turn.id"] = turn.turn_id
        parent = context.set_value("dialbb.service", PROCESS_SERVICE, context.Context())
        parent = context.set_value("dialbb.trace_attributes", attributes, parent)
        with operation("dialbb.process", parent=parent,
                       links=[trace.Link(caller)] if caller.is_valid else None) as span:
            target = span.get_span_context()
            if target.is_valid:
                caller_span.set_attribute("dialbb.process.trace_id", format(target.trace_id, "032x"))
            return function(self, request, initial=initial)
    return wrapped


@contextmanager
def block_operation(name, class_name, session_id, *, detailed=False):
    attributes = {"session.id": session_id, "block.name": name, "block.class": class_name}
    parent = context.get_current()
    inherited = context.get_value("dialbb.trace_attributes") or {}
    parent = context.set_value("dialbb.trace_attributes", {**inherited, **attributes}, parent)
    parent = context.set_value("dialbb.trace_features", detailed, parent)
    with operation("dialbb.block", attributes, parent=parent) as span:
        yield span


def traced_feature(name):
    """Trace a feature only while executing a selected configuration block."""
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            if not context.get_value("dialbb.trace_features"):
                return function(*args, **kwargs)
            with operation(name, {"code.function": function.__qualname__,
                                  "code.namespace": function.__module__}):
                return function(*args, **kwargs)
        return wrapped
    return decorate


@dataclass(slots=True, kw_only=True)
class TraceMessage:
    """Internal metadata only; never include this context in API payloads."""

    trace_context: context.Context = field(default_factory=context.get_current, repr=False, compare=False)
    queued_at_ns: int = field(default_factory=time_ns, repr=False, compare=False)
    queued_by_thread: str = field(default_factory=lambda: threading.current_thread().name, repr=False, compare=False)
    _queue_traced: bool = field(default=False, init=False, repr=False, compare=False)


@contextmanager
def message_operation(message: TraceMessage, name: str, *, queue_wait=True):
    """Restore a message's context without leaking it into the next request."""
    parent = message.trace_context
    turn = current_turn(parent)
    if turn is not None and turn.finished:
        parent = context.Context()
    attributes = {"queue.producer.thread": message.queued_by_thread,
                  "queue.consumer.thread": threading.current_thread().name}
    if turn is not None and not turn.finished:
        attributes["turn.id"] = turn.turn_id
    for key in ("session_id", "source", "utterance_id"):
        value = getattr(message, key, None)
        if value is not None:
            attributes[key.replace("_", ".")] = value
    if queue_wait and not message._queue_traced:
        now = time_ns()
        span = get_tracer(parent).start_span(
            name + ".queue_wait", context=parent, start_time=message.queued_at_ns,
            attributes=attributes,
        )
        span.end(end_time=now)
        message._queue_traced = True
    with operation(name, attributes, parent=parent) as span:
        yield span


def traced(name: str, message_arg: str | None = None, *, queue_wait=True):
    """Instrument synchronous processing boundaries, including queued messages."""
    def decorate(function):
        signature = inspect.signature(function)

        @wraps(function)
        def wrapped(*args, **kwargs):
            if message_arg:
                message = signature.bind(*args, **kwargs).arguments[message_arg]
                if getattr(getattr(message, "event_type", None), "value", None) == "aux_data":
                    return function(*args, **kwargs)
                scope = message_operation(message, name, queue_wait=queue_wait)
            else:
                scope = operation(name)
            with scope:
                return function(*args, **kwargs)
        return wrapped
    return decorate


def current_turn(parent=None):
    return context.get_value("dialbb.turn", parent)


def finish_turn(outcome, *, error=False):
    turn = current_turn()
    if turn is not None:
        turn.finish(outcome, error=error)


class ReceivedAudio(bytes):
    """PCM bytes with the original WebSocket receive timestamp (server only)."""

    def __new__(cls, audio, received_at_ns=None):
        instance = super().__new__(cls, audio)
        instance.received_at_ns = time_ns() if received_at_ns is None else received_at_ns
        return instance


class AudioTimeline:
    """Map STT stream offsets to received PCM16 mono chunks, without retaining audio."""

    def __init__(self, sample_rate):
        self.sample_rate = sample_rate
        self.frames = 0
        self.chunks = deque()
        self.lock = threading.Lock()

    def record(self, chunk):
        with self.lock:
            self.chunks.append((self.frames, getattr(chunk, "received_at_ns", time_ns())))
            self.frames += len(chunk) // 2

    @staticmethod
    def offset_seconds(offset):
        if offset is None:
            return None
        if hasattr(offset, "total_seconds"):
            return offset.total_seconds()
        return offset.seconds + offset.nanos / 1_000_000_000

    def received_at(self, offset=None):
        seconds = self.offset_seconds(offset)
        with self.lock:
            if not self.chunks:
                return time_ns(), "recognition_fallback"
            if seconds is None:
                return self.chunks[0][1], "first_unassigned_chunk"
            frame = int(seconds * self.sample_rate)
            while len(self.chunks) > 1 and self.chunks[1][0] <= frame:
                self.chunks.popleft()
            return self.chunks[0][1], "stt_speech_offset"

    def discard_before(self, offset):
        if offset is not None:
            self.received_at(offset)


class TurnRegistry:
    """Own unfinished turns for one browser session, including queued responses."""

    def __init__(self, session_id=""):
        self.session_id = session_id
        self.turns = set()
        self.lock = threading.RLock()
        self.closed = False

    def begin(self, started_at_ns, boundary):
        with self.lock:
            if self.closed:
                return None
            turn = TurnTrace(self, started_at_ns, boundary)
            self.turns.add(turn)
            return turn

    def close(self, outcome="session_closed"):
        with self.lock:
            self.closed = True
            turns = list(self.turns)
        for turn in turns:
            turn.finish(outcome)


class TurnTrace:
    def __init__(self, registry, started_at_ns, boundary):
        self.registry = registry
        self.lock = threading.RLock()
        self.finished = False
        self.scopes = set()
        self.turn_id = str(uuid.uuid4())
        self.root = get_tracer().start_span(
            "dialogue.turn", context=context.Context(), start_time=started_at_ns,
            attributes={"session.id": registry.session_id, "turn.id": self.turn_id,
                        "turn.start_boundary": boundary},
        )
        self.parent = context.set_value("dialbb.turn", self, trace.set_span_in_context(self.root))
        self.root.add_event("audio.first_received", timestamp=started_at_ns)

    def track_scope(self, span):
        with self.lock:
            if not self.finished:
                self.scopes.add(span)

    def end_scope(self, span):
        with self.lock:
            if span.is_recording():
                span.end()
            self.scopes.discard(span)

    def audio_sent(self, segment_index, segment_count):
        with self.lock:
            if self.finished:
                return
            self.root.add_event("audio.segment_sent", attributes={
                "segment.index": segment_index, "segment.count": segment_count,
            })
        if segment_count > 0 and segment_index == segment_count:
            self.finish()


    def finish(self, outcome="audio_sent", *, error=False):
        with self.lock:
            if self.finished:
                return
            self.finished = True
            ended_at = time_ns()
            self.root.set_attribute("turn.outcome", outcome)
            if error:
                self.root.set_status(trace.Status(trace.StatusCode.ERROR))
            for span in self.scopes:
                if span.is_recording():
                    span.end(end_time=ended_at)
            self.scopes.clear()
            self.root.end(end_time=ended_at)
        with self.registry.lock:
            self.registry.turns.discard(self)


class SpeechTrace:
    """STT child spans; the enclosing turn survives final transcription."""

    def __init__(self, registry=None, timeline=None):
        self.registry = registry if registry is not None else TurnRegistry()
        self.timeline = timeline
        self.turn = None
        self.root = None
        self.wait = None
        self.parent = None

    def annotate(self, event):
        if self.turn is not None and self.turn.finished:
            self.finish(transcribed=True)
        kind = event.event_type.value
        if kind in {"speech_started", "partial_transcript", "final_transcript"} and self.root is None:
            offset = getattr(event.raw, "speech_event_time", None) if kind == "speech_started" else None
            started_at, boundary = self.timeline.received_at(offset) if self.timeline else (time_ns(), "recognition_fallback")
            self.turn = self.registry.begin(started_at, boundary)
            if self.turn is None:
                return
            self.root = get_tracer().start_span(
                "stt.utterance", context=self.turn.parent, start_time=started_at,
            )
            self.turn.track_scope(self.root)
            self.parent = trace.set_span_in_context(self.root, self.turn.parent)
            self.root.add_event("stt.speech_detected")
        if self.root is None:
            return
        if kind == "speech_ended":
            self.root.add_event("stt.speech_ended")
            if self.wait is None:
                ended_at = time_ns()
                self.parent = context.set_value("dialbb.speech_end_ns", ended_at, self.parent)
                self.wait = get_tracer().start_span(
                    "stt.transcription_wait", context=self.parent, start_time=ended_at,
                )
                self.turn.track_scope(self.wait)
        if kind == "final_transcript":
            self.parent = context.set_value("dialbb.final_transcript_ns", time_ns(), self.parent)
        event.trace_context = self.parent
        if kind == "final_transcript":
            self.root.add_event("stt.final_transcript")
            if self.timeline is not None and getattr(event.raw, "results", None):
                self.timeline.discard_before(event.raw.results[0].result_end_time)
            self.finish(transcribed=True)
        elif kind == "error":
            self.finish()

    def finish(self, *, transcribed=False):
        for span in (self.wait, self.root):
            if span is not None:
                if self.turn is not None:
                    self.turn.end_scope(span)
                elif span.is_recording():
                    span.end()
        if self.turn is not None and not transcribed:
            self.turn.finish("recognition_interrupted")
        self.turn = self.root = self.wait = self.parent = None
