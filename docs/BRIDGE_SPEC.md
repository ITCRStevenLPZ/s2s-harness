# Bridge specification

`s2s serve` runs a small FastAPI app on `127.0.0.1:8787` so the two existing HTML tools become front ends for the shared engine instead of carrying their own duplicated JavaScript logic.

## Why keep the HTML at all

The forms are already built, already tested against the four worked examples, and the checkbox grid is a genuinely better input surface than sequential terminal prompts when you are flagging a dozen items. What must not survive is the **duplicated rules engine** — two implementations of the hierarchy walk will drift, and the drift will be silent.

So: keep the markup, delete the logic.

## Migration of the existing artifacts

`web/conversation.html` and `web/clips.html` are the current artifacts with these changes:

1. Delete `decide`, `validate`, `build`/`buildJustification`, and the scanner tables from the inline `<script>`.
2. Keep all markup, styling, chip rendering, and the DOM-diff guard that prevents a blur-triggered re-render from eating a chip click.
3. Replace `recompute()` with a debounced (250 ms) `POST /evaluate`, rendering the response.
4. Keep the `【placeholder】` highlighting — it now highlights markers produced server-side.
5. Delete the `window.claude.complete` path. Polishing happens server-side at the single sanctioned call site.

Net effect: the browser holds form state and rendering only. One engine, one set of rules, one place to fix a bug.

## Endpoints

### `POST /evaluate`
Body: `EvaluationState` fields as JSON (`context`, `a`, `b`, `picks`, `llm_enabled`).
Runs `scan → normalize → decide → audit → draft`, and `polish` only when `llm_enabled` is true and no blocking error exists.
Returns:

```json
{
  "verdict":     {"overall": "A", "driver": "…", "gated": true, "gated_side": "B", "trace": ["…"]},
  "findings":    [{"severity": "error", "code": "…", "label": "AUDIO", "message": "…"}],
  "suggestions": [{"side": "A", "target": "embodied", "kind": "error_cluster", "evidence": "…"}],
  "recommended": {"audio": "B", "overall": "A"},
  "draft":       "I prefer …",
  "polished":    "",
  "llm_skipped_reason": "blocking errors present"
}
```

Because the deterministic path costs nothing, this endpoint can safely be called on every keystroke-debounce — which is what makes the live-updating panel behave the same as it does today.

### `POST /polish`
Explicit, user-initiated polish for the "Generate with AI assist" button. Separating it from `/evaluate` means typing never triggers a model call. Returns 409 with the finding list when blocking errors exist.

### `POST /transcribe`
Multipart audio + `side`. Returns a `Transcript`. Lets the browser offer dictation with the same provider as the CLI.

### `GET /criteria/{topic}`
Serves `criteria/` as JSON so the cheat sheet in the HTML is rendered from the source of truth rather than duplicated in markup.

### `GET /health`
`{"ok": true, "stt": "gemini", "llm": true}` — lets the page show the same availability badge the artifacts show today.

## Security posture

- Bind `127.0.0.1` only. Never `0.0.0.0`.
- CORS allowlist: `null` (file:// pages) and `http://127.0.0.1:8787`.
- No auth — the surface is loopback-only and single-user. Do not add remote deployment without revisiting this.
- No request logging of note content by default; `--log-notes` opts in for debugging.

## Static serving

`GET /` serves `web/index.html`, a two-card chooser linking to the conversation and clip pages. Serving them from the same origin as the API avoids CORS entirely and lets the pages be opened as `http://127.0.0.1:8787/clips` rather than as local files.

## Parity requirement

`tests/test_parity.py` asserts that for every golden fixture, `POST /evaluate` returns a verdict, finding-code set, and draft byte-identical to the CLI's `--json` output for the same input. The bridge is a transport, not a second implementation, and this test is what keeps it that way.
