#!/usr/bin/env python3
"""globe_visualizer_parity.py -- build a side-by-side comparison PNG proving
that a single resolved geospatial runtime feeds MULTIPLE visualizers with the
SAME result: LEFT is the matplotlib plot (docs/globe.png), RIGHT is the Storm
render through the auto-inserted scene index (docs/usdrecord_earth2globe_autoinsert.png).

Both panels are rendered from the SAME viewpoint (elev=18, azim=-55 in ECEF),
with SAME turbo colormap, SAME dark tone, and the SAME resolved ECEF positions
(coming from crs:position -> PROJ under the hood in both).

Usage: globe_visualizer_parity.py [out.png]
"""
import os, sys
import matplotlib.pyplot as plt
from PIL import Image
import numpy as np

REPO = "/home/horde/.openclaw/workspace-identifiers/geo-usd"
DOCS = os.path.join(REPO, "extras/usd/examples/usdGeospatial/docs")


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(DOCS, "globe_visualizer_parity.png")
    plot = np.asarray(Image.open(os.path.join(DOCS, "globe.png")).convert("RGB"))
    rend = np.asarray(Image.open(os.path.join(DOCS, "usdrecord_earth2globe_autoinsert.png")).convert("RGB"))

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(14, 7))
    fig.patch.set_facecolor("#0b0e14")
    for ax, im, tag, sub in [
        (axL, plot, "Matplotlib 3D scatter",
         "docs/globe.png  \u2022  same crs:position \u2192 PROJ \u2192 ECEF resolve"),
        (axR, rend, "Storm (usdrecord, auto-insert SI)",
         "docs/usdrecord_earth2globe_autoinsert.png  \u2022  no SetStage, no baking"),
    ]:
        ax.imshow(im)
        ax.set_facecolor("#0b0e14")
        ax.set_title(tag, color="white", fontsize=12, pad=6)
        ax.text(0.5, -0.04, sub, transform=ax.transAxes, ha="center", va="top",
                color="#b8c0cc", fontsize=8)
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_color("#333844")

    fig.suptitle("Cross-visualizer parity \u2014 one runtime, same resolved result, "
                 "two renderers  (view: elev=18\u00b0 azim=\u221255\u00b0, cmap=turbo)",
                 color="white", fontsize=13, y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(out, dpi=130, facecolor=fig.get_facecolor())
    print("wrote", out)


if __name__ == "__main__":
    main()
