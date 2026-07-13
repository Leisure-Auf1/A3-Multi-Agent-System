"""
Phase 11 — Streaming Demo Utility

Provides token-level streaming simulation for real-time UX demonstration.
Integrates with EventBus for streaming event emission.

Supports:
- Token-by-token streaming simulation (time-based)
- Streaming event emission via EventBus
- Configurable delay between tokens
- Batch fallback for non-streaming providers
"""

from __future__ import annotations
import time
from typing import Callable, Iterator, List, Optional

from src.core.event_bus import AgentEventBus


class StreamingSimulator:
    """
    Simulates token-by-token streaming for demo purposes.

    Wraps a text response and yields tokens with configurable delays.
    Emits streaming events via EventBus for dashboard visualization.

    Usage:
        streamer = StreamingSimulator(delay_ms=50)

        # Basic streaming
        for token in streamer.stream("Hello, world!"):
            print(token, end="", flush=True)

        # Streaming with EventBus
        for token in streamer.stream_with_events(
            "Explain AI",
            agent_name="ContentAgent",
        ):
            print(token, end="", flush=True)
    """

    def __init__(
        self,
        delay_ms: int = 30,
        event_bus: Optional[AgentEventBus] = None,
    ):
        self.delay_ms = delay_ms
        self.bus = event_bus or AgentEventBus.get_instance()
        self._token_count = 0
        self._total_streamed = 0

    def stream(
        self,
        text: str,
        tokenizer: Optional[Callable[[str], List[str]]] = None,
        on_token: Optional[Callable[[str, int], None]] = None,
    ) -> Iterator[str]:
        """
        Stream text token by token with simulated delay.

        Args:
            text: The text to stream.
            tokenizer: Custom tokenizer function (default: space-split).
            on_token: Callback called with (token, index) for each token.

        Yields:
            One token string at a time.
        """
        tokens = self._tokenize(text, tokenizer)
        self._token_count = len(tokens)

        for i, token in enumerate(tokens):
            yield token
            self._total_streamed += 1

            if on_token:
                on_token(token, i)

            if i < len(tokens) - 1:
                time.sleep(self.delay_ms / 1000.0)

    def stream_with_events(
        self,
        text: str,
        agent_name: str = "StreamingAgent",
        action: str = "streaming_response",
        tokenizer: Optional[Callable[[str], List[str]]] = None,
    ) -> Iterator[str]:
        """
        Stream text and emit EventBus events for each token.

        This enables the Dashboard to show real-time streaming visualization.

        Args:
            text: The text to stream.
            agent_name: Agent name for EventBus events.
            action: Action label for EventBus events.
            tokenizer: Custom tokenizer function.

        Yields:
            One token string at a time.
        """
        tokens = self._tokenize(text, tokenizer)
        total = len(tokens)

        for i, token in enumerate(tokens):
            yield token
            self._total_streamed += 1

            # Emit streaming event
            self.bus.emit(
                agent=agent_name,
                action=action,
                input_summary=f"Token {i+1}/{total}",
                output_summary=token.strip(),
                status="streaming",
                duration_ms=self.delay_ms,
            )

            if i < len(tokens) - 1:
                time.sleep(self.delay_ms / 1000.0)

        # Emit completion event
        self.bus.emit(
            agent=agent_name,
            action=action,
            input_summary=f"Stream complete: {total} tokens",
            output_summary=text[:100] + ("..." if len(text) > 100 else ""),
            status="success",
            duration_ms=total * self.delay_ms,
        )

    def stream_batch(
        self,
        items: List[str],
        label: str = "item",
        on_batch_start: Optional[Callable[[int, str], None]] = None,
    ) -> Iterator[str]:
        """
        Stream a batch of items (e.g., multiple paragraphs, resource chunks).

        Args:
            items: List of text items to stream.
            label: Label for the items (e.g., "paragraph", "resource").
            on_batch_start: Callback before each item starts.

        Yields:
            Each item, one at a time.
        """
        for i, item in enumerate(items):
            if on_batch_start:
                on_batch_start(i, item)

            self.bus.emit(
                agent="StreamingAgent",
                action="batch_stream",
                input_summary=f"{label} {i+1}/{len(items)}",
                output_summary=item[:80] + ("..." if len(item) > 80 else ""),
                status="streaming",
            )

            yield item
            self._total_streamed += 1

            if i < len(items) - 1:
                time.sleep(self.delay_ms / 1000.0 * 3)  # Slightly longer between items

        self.bus.emit(
            agent="StreamingAgent",
            action="batch_stream",
            input_summary=f"Batch complete: {len(items)} {label}s",
            output_summary="",
            status="success",
        )

    def _tokenize(
        self,
        text: str,
        tokenizer: Optional[Callable[[str], List[str]]] = None,
    ) -> List[str]:
        """Tokenize text: custom tokenizer or default space-split."""
        if tokenizer:
            return tokenizer(text)
        # Default: split on spaces, preserve punctuation as separate tokens
        tokens = []
        for word in text.split():
            # Handle common punctuation
            if word and word[-1] in ",.!?;:)]}":
                tokens.append(word[:-1])
                tokens.append(word[-1])
            elif word and word[0] in "([{":
                tokens.append(word[0])
                tokens.append(word[1:])
            else:
                tokens.append(word)
        return [t for t in tokens if t]

    @property
    def stats(self) -> dict:
        return {
            "total_streamed": self._total_streamed,
            "last_batch_tokens": self._token_count,
            "delay_ms": self.delay_ms,
        }

    def reset(self):
        """Reset streaming counters."""
        self._token_count = 0
        self._total_streamed = 0


# ──────────────────────────────────────────────
# Demo streaming wrapper
# ──────────────────────────────────────────────

def demo_stream(text: str, delay_ms: int = 30) -> List[str]:
    """
    Quick demo: collect all streamed tokens into a list.
    Useful for testing that streaming works without waiting.

    Args:
        text: Text to stream.
        delay_ms: Delay between tokens.

    Returns:
        List of tokens in order.
    """
    # Temporarily set delay to 0 for fast collection
    streamer = StreamingSimulator(delay_ms=0)
    return list(streamer.stream(text))


def simulate_agent_stream(
    agent_name: str,
    response_text: str,
    delay_ms: int = 40,
) -> str:
    """
    Simulate an agent's streaming response with console output.
    Demonstrates the real-time streaming effect.

    Args:
        agent_name: Display name for the agent.
        response_text: Full response text.
        delay_ms: Delay between tokens for visual effect.

    Returns:
        The complete response text.
    """
    streamer = StreamingSimulator(delay_ms=delay_ms)
    collected = []

    print(f"\n[{agent_name}] ", end="", flush=True)
    for token in streamer.stream(response_text):
        collected.append(token)
        print(token, end="", flush=True)
    print()

    return "".join(collected)


# ──────────────────────────────────────────────
# CLI Demo
# ──────────────────────────────────────────────

if __name__ == "__main__":
    print("╔══════════════════════════════════╗")
    print("║  Streaming Demo — Simulation    ║")
    print("╚══════════════════════════════════╝")
    print()

    # Demo 1: Basic streaming
    print("─── Basic Streaming (50ms delay) ───")
    streamer = StreamingSimulator(delay_ms=50)
    for token in streamer.stream("Welcome to the multi-agent streaming demo!"):
        print(token, end="", flush=True)
    print("\n")

    # Demo 2: Fast collection (for testing)
    print("─── Fast Collection (0ms delay) ───")
    tokens = demo_stream("This is a test of fast token collection.")
    print(f"Collected {len(tokens)} tokens: {tokens}")
    print()

    # Demo 3: Agent simulation
    print("─── Agent Simulation ───")
    response = simulate_agent_stream(
        agent_name="ContentAgent",
        response_text="Here is your personalized learning content, generated in real-time!",
        delay_ms=40,
    )
    print(f"\nFinal response: {response}")
    print(f"Streaming stats: {streamer.stats}")
