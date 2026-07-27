"""Provider implementations of `s2s_harness.llm.client.Provider`.

Each submodule imports its own SDK lazily-safe (no network at import time)
and exposes exactly one `build_<name>_provider()` factory that reads its
required environment variable(s) and raises `LLMConfigError` if the API key
is missing. `s2s_harness.llm.client._build_provider` imports these
submodules on demand so that, e.g., a Gemini-only install does not require
the `openai` package to be importable, and vice versa.
"""
