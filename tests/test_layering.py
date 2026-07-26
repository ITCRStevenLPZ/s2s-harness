"""Cross-package invariants that only a test can enforce.

CLAUDE.md design rule 1 names this file as the home for the rules/
import-boundary test ("Enforced by: token-auditor plus an import-boundary
test in tests/test_layering.py"). This module holds the invariants that
`s2s_harness.models` and `s2s_harness.rules` agree on despite neither
package being allowed to import the other (`ARCHITECTURE.md`'s layer
table). Nothing at import time can catch those two definitions drifting
apart, since by construction neither module can see the other. These
tests are the enforcement mechanism instead.

Two teammates contribute here rather than each writing their own copy:
- `test_mode_literal_identical_across_layers` -- T2-rules-engine-dev and
  T3-graph-architect, agreed via team_findings.md.
- `test_catalogue_key_defaults_identical_across_layers` -- T3-graph-architect,
  added when the lead's review found `models.state.SideObservation`'s
  unknown-flag-key validator failed open with no `context` supplied. The
  fix hardcodes a fail-closed default vocabulary directly in
  `models/state.py` (duplicating `rules/catalog.py`'s key tuples, since
  importing them is not allowed); this test is what keeps that
  duplication honest.
"""

from __future__ import annotations

import typing

from s2s_harness.models import state as models_state
from s2s_harness.models.state import Mode as StateMode
from s2s_harness.rules import catalog
from s2s_harness.rules.catalog import Mode as CatalogMode


def test_mode_literal_identical_across_layers() -> None:
    """`rules.catalog.Mode` and `models.state.Mode` must never drift apart.

    Both packages define `Mode = Literal["conversation", "clips"]`
    independently because the layer boundary forbids a shared import. If a
    future edit adds, removes or renames a mode in one file without
    mirroring it in the other, this assertion fails the build rather than
    letting the two Literals silently diverge.
    """
    assert typing.get_args(CatalogMode) == typing.get_args(StateMode)


def test_catalogue_key_defaults_identical_across_layers() -> None:
    """`models.state`'s hardcoded fail-closed default key sets must never
    drift from `rules.catalog`'s exported tuples.

    `SideObservation._flag_keys_known` cannot import `rules.catalog` (layer
    boundary), so it carries its own copy of the closed vocabulary as its
    fail-closed default. If a future edit adds, removes or renames a
    catalogue key in `rules/catalog.py` without mirroring it here, this
    assertion fails the build instead of letting the two catalogues
    silently diverge -- the same guarantee `test_mode_literal_identical_
    across_layers` gives `Mode`, applied to the five key sets the
    unknown-flag-key validator depends on.
    """
    assert models_state._ERROR_CLUSTER_KEYS == frozenset(catalog.ERROR_CLUSTER_KEYS)
    assert models_state._THRESHOLD_UTILITY_KEYS == frozenset(catalog.THRESHOLD_UTILITY_KEYS)
    assert models_state._THRESHOLD_UTILITY_INPUT_KEYS == frozenset(
        catalog.THRESHOLD_UTILITY_INPUT_KEYS
    )
    assert models_state._THRESHOLD_AUDIO_KEYS == frozenset(catalog.THRESHOLD_AUDIO_KEYS)
    assert models_state._THRESHOLD_AUDIO_INPUT_KEYS == frozenset(catalog.THRESHOLD_AUDIO_INPUT_KEYS)
