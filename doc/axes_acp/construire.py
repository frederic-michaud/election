"""Compose doc/axes_acp.pdf à partir de axes_acp.typ (Typst) et de resultats.json.

    python doc/axes_acp/construire.py

Lancer d'abord analyse.py, qui écrit resultats.json et les figures.
"""

from pathlib import Path

import typst

ICI = Path(__file__).resolve().parent
SORTIE = ICI.parent / "axes_acp.pdf"

if __name__ == "__main__":
    typst.compile(str(ICI / "axes_acp.typ"), output=str(SORTIE), root=str(ICI))
    print(f"→ {SORTIE} ({SORTIE.stat().st_size // 1024} Ko)")
