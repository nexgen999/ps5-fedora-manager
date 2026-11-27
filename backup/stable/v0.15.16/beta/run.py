#!/usr/bin/env python3
"""Point d'entrée de l'édition bêta : `python3 beta/run.py`.

La version stable reste à la racine du dépôt ; ce script ne charge que `beta/`.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ps5m.app import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
