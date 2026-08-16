"""
demo.py
=======

Headless smoke test / figure generator -- runs the engine with no Streamlit,
no browser, no network. Useful for CI, for profiling, and for checking that a
parameter set behaves before wiring it into the UI.

    python demo.py --region "Contiguous USA" --preset "Wind-dispersed weed" --steps 100
"""

from __future__ import annotations

import argparse

import numpy as np

from data import REGIONS, synthetic_environment
from model import Simulator
from species import get_preset, preset_names


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--region", default="Pacific Northwest", choices=list(REGIONS))
    ap.add_argument("--preset", default="Thermophilic insect", choices=preset_names())
    ap.add_argument("--resolution", type=float, default=None)
    ap.add_argument("--steps", type=int, default=100)
    ap.add_argument("--n0", type=float, default=500.0)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--figure", default="invasion.png", help="output PNG (empty to skip)")
    args = ap.parse_args()

    grid = REGIONS[args.region].to_grid(args.resolution)
    env = synthetic_environment(grid, seed=args.seed)
    species = get_preset(args.preset)
    sim = Simulator(env, species, seed=args.seed)

    # Release at the most suitable land cell so the demo always establishes.
    row, col = np.unravel_index(int(np.argmax(sim.suitability)), sim.suitability.shape)
    if not sim.seed_at(int(row), int(col), n0=args.n0, radius_cells=1):
        raise SystemExit("no habitable cell for this species in this region")

    print(f"{args.preset} in {args.region}  |  grid {grid.n_rows}x{grid.n_cols}, "
          f"cell {grid.cell_width_km:.0f}x{grid.cell_height_km:.0f} km")
    print(f"habitable: {(sim.suitability > 0).sum():,} cells, "
          f"mean S = {sim.suitability[sim.suitability > 0].mean():.2f}")

    snapshots, snap_steps = [], []
    every = max(1, args.steps // 4)
    for t in range(1, args.steps + 1):
        sim.step()
        if t % every == 0 and len(snapshots) < 4:
            snapshots.append(sim.N.copy())
            snap_steps.append(t)

    print(f"\n{'step':>6} {'total N':>14} {'cells':>8} {'front km':>10} {'v km/step':>10}")
    for m in sim.metrics[:: max(1, len(sim.metrics) // 10)]:
        print(f"{m.step:6d} {m.total_population:14,.0f} {m.occupied_cells:8d} "
              f"{m.front_km:10.1f} {m.frontier_speed_km:10.2f}")

    if args.figure:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(2, 4, figsize=(18, 9))
        panels = [
            (env.temperature, "coolwarm", "Temperature (°C)"),
            (env.precipitation, "YlGnBu", "Precipitation (mm/yr)"),
            (env.land_mask.astype(float), "gray", "Land mask"),
            (sim.suitability, "YlGn", "Habitat suitability S"),
        ]
        for ax, (data, cmap, title) in zip(axes[0], panels):
            ax.imshow(data, cmap=cmap)
            ax.set_title(title, fontsize=11)
        for ax, frame, t in zip(axes[1], snapshots, snap_steps):
            ax.imshow(env.land_mask, cmap="gray", alpha=0.25)
            ax.imshow(np.where(frame > 0, frame, np.nan), cmap="inferno")
            ax.set_title(f"Population, t = {t}", fontsize=11)
        for ax in axes.ravel():
            ax.set_xticks([])
            ax.set_yticks([])
        fig.suptitle(f"{args.preset} — {args.region}", fontsize=14)
        fig.tight_layout()
        fig.savefig(args.figure, dpi=110)
        print(f"\nwrote {args.figure}")


if __name__ == "__main__":
    main()
