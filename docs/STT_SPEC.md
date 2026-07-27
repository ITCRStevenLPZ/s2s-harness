# Speech-to-text specification

Version: 1.0.0
Last updated: 2026-07-26

**ID convention:** `STT-n` trailing tag `{STT-n}`, one to two per `##` section depending on how many distinct requirements it states, assigned once in document order. IDs are additive only; no requirement text below was reworded, reordered or removed to add them.

The rater dictates their observations instead of typing them. Richer notes get captured, faster, while the audio is still fresh — and richer notes are the single biggest lever on justification quality, because every sentence the engine writes is built from what the rater actually recorded.

Credentials are supplied by the operator and are **not** in this repo.

---

## 1. Scope {STT-1}

| In scope | Out of scope |
|---|---|
| Transcribing the **rater's spoken notes** about each side | Transcribing or analysing the **model clips** (see §6) |
| Spanish (es-CR / es-419) and English, auto-detected | Any language the rater is not authorized to work in |
| Word-level timing when the provider returns it | Speaker diarization — single speaker by definition |

---

## 2. Provider interface {STT-2}

`src/s2s_harness/stt/base.py`

```python
class Word(BaseModel):
    text: str
    start_s: float | None = None
    end_s: float | None = None

class Transcript(BaseModel):
    text: str
    language: str | None = None
    words: list[Word] = []
    provider: str
    duration_s: float | None = None
    raw: dict | None = None          # provider payload, for debugging only

class TranscriptionProvider(Protocol):
    name: str
    def transcribe(
        self,
        audio: Path,
        *,
        languages: list[str],
        phrase_hints: list[str],
    ) -> Transcript: ...
```
{STT-3}

Selection via `S2S_STT_PROVIDER` in `{gemini, gcp, null}`, default `null`. Unknown value → hard error at startup, never a silent fallback. {STT-4}

---

## 3. `GeminiTranscriber` {STT-5}

SDK: `google-genai`. Auth: `GEMINI_API_KEY`.

- Upload the audio file, request a transcription with an explicit instruction to transcribe **verbatim**, preserving hesitations and self-corrections, and to output nothing but the transcript.
- Prime domain vocabulary by listing the phrase hints in the instruction — this is Gemini's equivalent of speech adaptation and materially improves recall on the terms that matter.
- Do not ask the model to summarize, clean up, or interpret the notes. A summary loses exactly the specific detail the justification depends on.
- Word timings: request them when the model supports it; tolerate their absence.
- Retry: 2 attempts with exponential backoff on transient errors; on final failure raise `TranscriptionError` with the file path — never return an empty transcript that silently becomes empty notes.

## 4. `GoogleCloudSTT` {STT-6}

SDK: `google-cloud-speech` v2. Auth: `GOOGLE_APPLICATION_CREDENTIALS` pointing at a service-account JSON.

- `RecognitionConfig` with `language_codes=["es-CR", "en-US"]` for automatic multilingual detection, `enable_automatic_punctuation=True`, `enable_word_time_offsets=True`, `model="latest_long"`.
- Attach the phrase hints as a `SpeechAdaptation` phrase set with a moderate boost (≈15). Over-boosting causes the recognizer to hallucinate the boosted terms into unrelated audio — which in this application would fabricate flags. Keep the boost conservative and verify against the fixture recordings.
- Files over ~60 s go through `BatchRecognize`; shorter ones use the synchronous path.

## 5. Phrase hints {STT-7}

`src/s2s_harness/stt/phrase_hints.py`. These are the terms that decide whether the scanner fires, so recognition accuracy on them is worth more than general WER.

**Spanish:** chasquido · corte de audio · se corta · a media palabra · distorsión · entrecortado · estática · ruido de fondo · premisa falsa · alucinación · se lo inventó · me interrumpió · me habló encima · no me dejó hablar · silencio incómodo · pausa larga · robótico · monótono · acartonado · cálido · natural · expresivo · turno uno · turno dos · turno tres · turno cuatro

**English:** click · pop · crackle · cut off · mid-word · distortion · dropout · static · background noise · room tone · false premise · hallucination · made up · talked over · interrupted me · awkward silence · robotic · monotone · flat delivery · warm · natural · expressive · turn one · turn two · turn three · turn four

Load from a data file, not a literal in code, so the rater can extend it without touching Python.

---

## 6. What the STT layer must not do

The project requires that the rater's own ears produce the audio-quality judgement, on phase-aligned stereo headphones. That is not a preference the harness may optimize away.

Therefore:

- **No provider ever receives a model clip in the default path.** Only the rater's dictated notes. {STT-8}
- An optional `ClipAnalyzer` adapter may be built behind the `S2S_EXPERIMENTAL_CLIP_ANALYSIS` flag, **off by default**. If built, it is bound by three rules: its output enters state as `Suggestion` objects only, never as flags; every suggestion it produces is labelled as machine-detected in the UI; and it may not contribute to `Verdict` or to any `Finding`. It is a second opinion that prompts the rater to relisten, never a substitute for listening. {STT-9}
- The transcript is never fed to the rules engine as prose to be interpreted. It becomes `notes`, and `notes` are read by regex only. {STT-10}

---

## 7. Audio capture {STT-11}

`s2s ... --dictate` records from the default input device via `sounddevice`, writes 16 kHz mono WAV to a temp path, and passes it to the provider. Press Enter to stop. `--notes-a PATH` / `--notes-b PATH` skip recording and transcribe an existing file (m4a, mp3, wav, flac).

Transcripts are **appended** to any typed notes, never substituted, so mixing typing and dictation works.

Temp recordings are deleted after transcription unless `--keep-audio` is passed.

---

## 8. Failure behavior {STT-12}

| Failure | Behavior |
|---|---|
| No credentials configured | Startup error naming the missing env var. Never silently degrade to `null`. |
| Provider raises | `TranscriptionError`; the CLI offers to retry, type the notes instead, or abort. The graph never proceeds with silently empty notes. |
| Empty transcript returned | Treated as a failure, not as empty notes. |
| Audio device unavailable | Fall back to prompting for a file path. |

---

## 9. Cost note {STT-13}

Transcription is billed by the provider, separately from the single completion in `polish`. A dictated evaluation therefore costs one STT call per side plus one short completion. This is still the cheapest configuration that captures good notes, because the alternative — the rater typing less because typing is slow — degrades every downstream sentence.
