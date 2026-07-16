from __future__ import annotations

import warnings

warnings.warn(
    "services.bootstrap is deprecated. Import from core.bootstrap instead. "
    "This module will be removed in a future release.",
    DeprecationWarning,
    stacklevel=2,
)

from core.bootstrap import boot, load_baseline  # noqa: E402

__all__ = ["boot", "load_baseline"]
