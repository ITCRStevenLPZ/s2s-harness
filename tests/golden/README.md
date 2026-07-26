# Golden fixtures

YAML fixtures encoding the project's worked examples plus adversarial cases. Written **before** the engine, per `docs/BUILD_PLAN.md` Phase 3 — the engine is developed against known-correct answers rather than validated after the fact.

Required set and the fixture format are in `docs/EVAL_SPEC.md`. Reference answers are in `criteria/worked-examples.md`.

A change that flips a fixture is wrong by default. Changing one requires a corresponding change to `criteria/` in the same commit.
