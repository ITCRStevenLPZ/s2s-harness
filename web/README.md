# Front ends

`conversation.html` and `clips.html` are the two original standalone artifacts, copied here **unmodified** as the porting starting point.

They currently carry their own complete JavaScript rules engine. That duplication is the thing this repository exists to remove: two implementations of the hierarchy walk will drift, and the drift will be silent.

See `docs/BRIDGE_SPEC.md` for the porting checklist. In short — keep the markup, the styling, the chip rendering and the DOM-diff guard; delete `decide`, `validate`, `build`, the scanner tables and the direct model call; replace `recompute()` with a debounced `POST /evaluate`.

Until that port lands, these files still work standalone by opening them directly in a browser.
