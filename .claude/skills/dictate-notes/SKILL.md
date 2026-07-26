---
name: dictate-notes
description: Capture S2S Arena rating observations by voice and transcribe them with Gemini or Google Cloud Speech-to-Text. Use when the rater wants to speak their notes instead of typing, has an audio recording of their observations, or asks about setting up voice input.
---

# Dictate rating notes

Speaking notes captures more detail than typing does, while the audio is still fresh — and every sentence the harness writes is built from those notes.

## Capture

```
uv run s2s clips --dictate                  # record per side from the mic
uv run s2s clips --notes-a notes_a.m4a      # transcribe an existing recording
```

Transcripts **append** to typed notes rather than replacing them, so typing a little and dictating the rest works.

## What to say

Dictate the way you would tell a colleague what you heard. Name the turn or moment, then what happened. The scanner is looking for concrete terms, so say them plainly: *"turno tres, se cortó a media palabra"*, *"turn two, it talked over me and didn't stop"*, *"chasquido al final"*, *"sonó robótico y monótono"*.

Avoid summarizing. "Clip B was worse" gives the engine nothing; "Clip B cut off mid-word at the end and there was an audible pop" gives it a threshold flag, an evidence sentence and an audio statement.

## Setup

Set one of these, then select the provider:

```
GEMINI_API_KEY=...                    S2S_STT_PROVIDER=gemini
GOOGLE_APPLICATION_CREDENTIALS=...    S2S_STT_PROVIDER=gcp
```

Spanish and English are both recognized and auto-detected. Domain terms are boosted through phrase hints; extend the list in the phrase-hints data file if you find a term being missed consistently.

## Boundaries

Speech-to-text transcribes **your notes**. It never listens to the model clips and never produces an audio-quality judgement — the project requires that to come from your own ears on stereo headphones.

If transcription fails, it fails loudly. Retry, type instead, or abort — the harness will not quietly proceed with empty notes.

## Reference

`docs/STT_SPEC.md`
