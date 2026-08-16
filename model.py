"""
model.py
========

Core vectorised simulation engine for the Species Distribution & Dispersal
Simulator.

The engine is a reaction--diffusion cellular model on a regular lat/lon grid:

    1. **Niche filter**   S(x, y) in [0, 1]  -- Gaussian tolerance curves on
       one or more environmental layers (temperature, precipitation, ...).
    2. **Reaction**       Discrete logistic growth with suitability-scaled
       carrying capacity and a density-independent mortality term.
    3. **Diffusion**      Convolution of the population field with a normalised
       2D dispersal kernel (Gaussian, exponential, or fat-tailed).

Everything is NumPy/SciPy vectorised -- no Python-level loops over cells --
so a 400 x 400 grid runs several hundred steps per second.

Design notes
------------
*   All tunable quantities live in small frozen-ish dataclasses so the UI can
    rebuild them cheaply every rerun.
*   ``Simulator`` owns mutable state (``N``, ``t``, ``history``) and nothing
    else; the pure math lives in module-level functions that are trivially
    unit-testable.
*   Dispersal is *mass conserving* by construction when
    ``boundary="reflecting"``: each source cell renormalises its kernel over
    the subset of targets that are actually habitable, so no individuals are
    silently created or destroyed at coastlines and grid edges.

Author: computational-ecology reference implementation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Callable, Dict, List, Literal, Optional, Sequence, Tuple

import numpy as np
from scipy import ndimage
from scipy.signal import fftconvolve

__all__ = [
    "GridSpec",
    "Environment",
    "NicheParams",
    "DemographyParams",
    "DispersalParams",
    "SpeciesParams",
    "StepMetrics",
    "Simulator",
    "gaussian_response",
    "habitat_suitability",
    "logistic_step",
    "make_dispersal_kernel",
    "disperse",
]

EARTH_RADIUS_KM = 6371.0088
KernelName = Literal["gaussian", "exponential", "fat_tail"]
Boundary = Literal["absorbing", "reflecting"]


# --------------------------------------------------------------------------- #
# Grid geometry
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class GridSpec:
    """A regular geographic grid in EPSG:4326.

    Row 0 is the *north* edge (standard raster orientation), so ``lats`` is
    monotonically decreasing.
    """

    west: float
    south: float
    east: float
    north: float
    n_rows: int
    n_cols: int

    # -- derived ---------------------------------------------------------- #
    @property
    def dlon(self) -> float:
        return (self.east - self.west) / self.n_cols

    @property
    def dlat(self) -> float:
        return (self.north - self.south) / self.n_rows

    @property
    def shape(self) -> Tuple[int, int]:
        return self.n_rows, self.n_cols

    @property
    def lons(self) -> np.ndarray:
        """Cell-centre longitudes, shape (n_cols,)."""
        return self.west + (np.arange(self.n_cols) + 0.5) * self.dlon

    @property
    def lats(self) -> np.ndarray:
        """Cell-centre latitudes, shape (n_rows,), decreasing north -> south."""
        return self.north - (np.arange(self.n_rows) + 0.5) * self.dlat

    @property
    def mesh(self) -> Tuple[np.ndarray, np.ndarray]:
        """``(lon2d, lat2d)`` broadcast to the full grid shape."""
        return np.meshgrid(self.lons, self.lats)

    @property
    def mean_lat(self) -> float:
        return 0.5 * (self.north + self.south)

    @property
    def cell_height_km(self) -> float:
        """North--south extent of one cell in kilometres."""
        return self.dlat * math.pi / 180.0 * EARTH_RADIUS_KM

    @property
    def cell_width_km(self) -> float:
        """East--west extent of one cell at the grid's mean latitude."""
        return (
            self.dlon
            * math.pi
            / 180.0
            * EARTH_RADIUS_KM
            * math.cos(math.radians(self.mean_lat))
        )

    @property
    def cell_area_km2(self) -> float:
        return self.cell_width_km * self.cell_height_km

    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        """``(west, south, east, north)`` -- the order pydeck/folium expect."""
        return self.west, self.south, self.east, self.north

    def lonlat_to_rc(self, lon: float, lat: float) -> Optional[Tuple[int, int]]:
        """Map a geographic coordinate to ``(row, col)``; ``None`` if outside."""
        if not (self.west <= lon <= self.east and self.south <= lat <= self.north):
            return None
        col = int((lon - self.west) / self.dlon)
        row = int((self.north - lat) / self.dlat)
        col = min(max(col, 0), self.n_cols - 1)
        row = min(max(row, 0), self.n_rows - 1)
        return row, col

    def rc_to_lonlat(self, row: int, col: int) -> Tuple[float, float]:
        return (
            self.west + (col + 0.5) * self.dlon,
            self.north - (row + 0.5) * self.dlat,
        )

    def distance_km_from(self, row: int, col: int) -> np.ndarray:
        """Euclidean-on-the-local-tangent-plane distance field from one cell."""
        rr, cc = np.indices(self.shape)
        dy = (rr - row) * self.cell_height_km
        dx = (cc - col) * self.cell_width_km
        return np.hypot(dx, dy)


# --------------------------------------------------------------------------- #
# Environment
# --------------------------------------------------------------------------- #
@dataclass
class Environment:
    """Stack of environmental layers aligned to a :class:`GridSpec`.

    Parameters
    ----------
    grid
        Geographic definition of the raster.
    temperature
        Mean annual temperature, degrees Celsius, shape ``grid.shape``.
    precipitation
        Annual precipitation, mm/yr, shape ``grid.shape``.
    land_mask
        Boolean array; ``False`` cells are permanently uninhabitable (ocean,
        ice, nodata). Defaults to all-land.
    name
        Free-form label used by the UI.
    """

    grid: GridSpec
    temperature: np.ndarray
    precipitation: np.ndarray
    land_mask: Optional[np.ndarray] = None
    name: str = "environment"

    def __post_init__(self) -> None:
        shape = self.grid.shape
        self.temperature = np.asarray(self.temperature, dtype=np.float32)
        self.precipitation = np.asarray(self.precipitation, dtype=np.float32)
        if self.temperature.shape != shape:
            raise ValueError(
                f"temperature shape {self.temperature.shape} != grid {shape}"
            )
        if self.precipitation.shape != shape:
            raise ValueError(
                f"precipitation shape {self.precipitation.shape} != grid {shape}"
            )
        if self.land_mask is None:
            self.land_mask = np.ones(shape, dtype=bool)
        else:
            self.land_mask = np.asarray(self.land_mask, dtype=bool)
            if self.land_mask.shape != shape:
                raise ValueError("land_mask shape does not match grid")

    @property
    def layers(self) -> Dict[str, np.ndarray]:
        return {
            "temperature": self.temperature,
            "precipitation": self.precipitation,
        }


# --------------------------------------------------------------------------- #
# Parameters
# --------------------------------------------------------------------------- #
@dataclass
class NicheParams:
    """Gaussian tolerance curves defining the fundamental niche."""

    t_opt: float = 18.0           # thermal optimum, degC
    t_tol: float = 7.0            # thermal tolerance (sigma), degC
    p_opt: float = 1000.0         # precipitation optimum, mm/yr
    p_tol: float = 700.0          # precipitation tolerance (sigma), mm/yr
    use_precipitation: bool = True
    #: Cells below this suitability are treated as hard-unsuitable (S := 0).
    suitability_floor: float = 0.02


@dataclass
class DemographyParams:
    """Local (within-cell) population dynamics."""

    r: float = 0.35               # intrinsic growth rate, per step
    K: float = 1000.0             # carrying capacity of a *perfect* cell
    mortality: float = 0.02       # density-independent per-step mortality
    allee_threshold: float = 0.0  # N below this in a cell -> extirpation
    #: Populations below this are zeroed to keep the front crisp and the
    #: occupied-area metric meaningful.
    extinction_floor: float = 1e-3


@dataclass
class DispersalParams:
    """Kernel-based spread between cells."""

    sigma_km: float = 25.0        # characteristic dispersal distance
    kernel: KernelName = "gaussian"
    fraction: float = 0.25        # proportion of each cell's pop. that moves
    #: Kernel truncation radius as a multiple of ``sigma``. Larger = more
    #: accurate tails, quadratically more expensive.
    truncate: float = 3.0
    boundary: Boundary = "reflecting"
    #: Optional rare long-distance jumps (per-cell probability per step).
    jump_probability: float = 0.0
    jump_distance_km: float = 300.0
    #: Fat-tail kernel shape exponent (only used when kernel="fat_tail").
    fat_tail_alpha: float = 2.5


@dataclass
class SpeciesParams:
    """Everything that defines one species."""

    name: str = "Custom species"
    niche: NicheParams = field(default_factory=NicheParams)
    demography: DemographyParams = field(default_factory=DemographyParams)
    dispersal: DispersalParams = field(default_factory=DispersalParams)
    notes: str = ""

    def evolve(self, **kwargs) -> "SpeciesParams":
        """Return a copy with top-level fields replaced (handy in Streamlit)."""
        return replace(self, **kwargs)


# --------------------------------------------------------------------------- #
# Niche / suitability
# --------------------------------------------------------------------------- #
def gaussian_response(x: np.ndarray, opt: float, tol: float) -> np.ndarray:
    r"""Gaussian tolerance curve.

    .. math::
        f(x) = \exp\!\left(-\frac{(x - x_{opt})^2}{2\,\sigma^2}\right)

    Returns 1.0 at the optimum and decays smoothly. ``tol <= 0`` degenerates to
    a step function (perfect specialist), which we approximate with an
    arbitrarily small sigma to avoid division by zero.
    """
    tol = max(float(tol), 1e-6)
    return np.exp(-0.5 * ((np.asarray(x, dtype=np.float32) - opt) / tol) ** 2)


def habitat_suitability(env: Environment, niche: NicheParams) -> np.ndarray:
    r"""Multiplicative (Liebig-style) niche envelope, :math:`S \in [0, 1]`.

    Temperature and precipitation responses are combined multiplicatively so a
    cell must satisfy *every* axis to be suitable -- the standard bioclimatic
    envelope assumption. The land mask is applied last.
    """
    s = gaussian_response(env.temperature, niche.t_opt, niche.t_tol)
    if niche.use_precipitation:
        s = s * gaussian_response(env.precipitation, niche.p_opt, niche.p_tol)

    s = np.where(s < niche.suitability_floor, 0.0, s)
    s = s * env.land_mask
    return s.astype(np.float32)


# --------------------------------------------------------------------------- #
# Local dynamics
# --------------------------------------------------------------------------- #
def logistic_step(
    N: np.ndarray,
    suitability: np.ndarray,
    demo: DemographyParams,
) -> np.ndarray:
    r"""One step of suitability-scaled discrete logistic growth.

    .. math::
        N_{t+1} = N_t + r\,N_t\left(1 - \frac{N_t}{K\,S}\right) - m\,N_t

    Cells with :math:`S = 0` have zero capacity and are extirpated outright
    (the ratio :math:`N/(KS)` is undefined there, so it is short-circuited
    rather than clipped). Growth is clipped at ``-N`` so a large ``r`` cannot
    drive a cell negative; densities are clipped at ``2 K S`` to keep
    overshoot-driven oscillations bounded rather than divergent.
    """
    capacity = demo.K * suitability
    habitable = capacity > 0.0

    # Safe division: unsuitable cells get a dummy capacity and are masked out.
    safe_capacity = np.where(habitable, capacity, 1.0)
    growth = demo.r * N * (1.0 - N / safe_capacity)
    growth = np.maximum(growth, -N)  # never remove more than is present

    N_next = N + growth - demo.mortality * N
    N_next = np.where(habitable, N_next, 0.0)

    # Bound overshoot: chaotic logistic maps are a numerical nuisance, not
    # ecology, at the r values this tool exposes.
    N_next = np.clip(N_next, 0.0, 2.0 * capacity)

    if demo.allee_threshold > 0.0:
        N_next = np.where(N_next < demo.allee_threshold, 0.0, N_next)
    N_next = np.where(N_next < demo.extinction_floor, 0.0, N_next)
    return N_next.astype(np.float32)


# --------------------------------------------------------------------------- #
# Dispersal
# --------------------------------------------------------------------------- #
def make_dispersal_kernel(
    grid: GridSpec,
    params: DispersalParams,
) -> np.ndarray:
    r"""Build a normalised, anisotropy-aware 2D dispersal kernel.

    Because a lat/lon cell is wider in metres north--south than east--west
    (away from the equator the reverse), the kernel is built in *kilometres*
    and then sampled on the cell lattice, giving the correct elliptical
    footprint in index space.

    Kernels (all functions of radial distance :math:`d` in km):

    ``gaussian``     :math:`\exp(-d^2 / 2\sigma^2)` -- classic diffusion,
                     thin tails, well-behaved travelling wave.
    ``exponential``  :math:`\exp(-d / \sigma)`      -- leptokurtic, the usual
                     empirical fit for seed and larval dispersal.
    ``fat_tail``     :math:`(1 + d/\sigma)^{-\alpha}` -- power-law tail that
                     produces accelerating, patchy invasions.

    Returns
    -------
    ndarray
        Odd-sized 2D array summing to exactly 1.
    """
    sigma = max(float(params.sigma_km), 1e-6)
    reach_km = params.truncate * sigma
    if params.kernel == "fat_tail":
        reach_km *= 2.0  # power-law tails need more room to matter

    ry = max(1, int(math.ceil(reach_km / grid.cell_height_km)))
    rx = max(1, int(math.ceil(reach_km / grid.cell_width_km)))
    # Guard against pathological kernel sizes on fine grids.
    ry, rx = min(ry, 60), min(rx, 60)

    dy = np.arange(-ry, ry + 1)[:, None] * grid.cell_height_km
    dx = np.arange(-rx, rx + 1)[None, :] * grid.cell_width_km
    d = np.hypot(dy, dx)

    if params.kernel == "gaussian":
        w = np.exp(-0.5 * (d / sigma) ** 2)
    elif params.kernel == "exponential":
        w = np.exp(-d / sigma)
    elif params.kernel == "fat_tail":
        w = (1.0 + d / sigma) ** (-float(params.fat_tail_alpha))
    else:  # pragma: no cover - guarded by Literal typing
        raise ValueError(f"unknown kernel {params.kernel!r}")

    total = w.sum()
    if total <= 0:  # pragma: no cover
        raise ValueError("degenerate dispersal kernel")
    return (w / total).astype(np.float32)


def _convolve(field_: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """Same-size zero-padded convolution, FFT-accelerated for big kernels."""
    if kernel.size >= 121:
        out = fftconvolve(field_, kernel, mode="same")
        return np.maximum(out, 0.0)  # kill FFT round-off negatives
    return ndimage.convolve(field_, kernel, mode="constant", cval=0.0)


def disperse(
    N: np.ndarray,
    kernel: np.ndarray,
    habitable: np.ndarray,
    params: DispersalParams,
    _norm_cache: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Redistribute the mobile fraction of each cell's population.

    ``boundary="reflecting"`` renormalises every source cell's kernel over the
    habitable targets within reach, so total population is conserved exactly
    (up to floating point) even against a coastline. ``"absorbing"`` lets
    propagules that land in the ocean or off-grid die, which is the more
    realistic choice for a marine barrier.
    """
    f = float(np.clip(params.fraction, 0.0, 1.0))
    if f <= 0.0:
        return N.copy()

    mobile = f * N
    stay = N - mobile

    if params.boundary == "reflecting":
        norm = _norm_cache if _norm_cache is not None else _convolve(
            habitable.astype(np.float32), kernel
        )
        safe = np.where(norm > 1e-12, norm, 1.0)
        moved = _convolve(np.where(norm > 1e-12, mobile / safe, 0.0), kernel)
    else:
        moved = _convolve(mobile, kernel)

    out = stay + moved * habitable
    return np.maximum(out, 0.0).astype(np.float32)


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
@dataclass
class StepMetrics:
    """Summary statistics recorded once per time step."""

    step: int
    total_population: float
    occupied_cells: int
    occupied_area_km2: float
    mean_density: float
    front_km: float          # furthest occupied cell from the seed
    frontier_speed_km: float  # change in front_km since the previous step

    def as_dict(self) -> Dict[str, float]:
        return {
            "step": self.step,
            "total_population": self.total_population,
            "occupied_cells": self.occupied_cells,
            "occupied_area_km2": self.occupied_area_km2,
            "mean_density": self.mean_density,
            "front_distance_km": self.front_km,
            "front_speed_km_per_step": self.frontier_speed_km,
        }


# --------------------------------------------------------------------------- #
# Simulator
# --------------------------------------------------------------------------- #
class Simulator:
    """Stateful driver: holds the population field and advances it in time.

    Example
    -------
    >>> sim = Simulator(env, SpeciesParams())
    >>> sim.seed(lon=-123.1, lat=49.3, n0=500.0, radius_cells=1)
    >>> sim.run(50)
    >>> sim.metrics[-1].total_population > 0
    True
    """

    def __init__(
        self,
        env: Environment,
        species: SpeciesParams,
        record_history: bool = True,
        history_stride: int = 1,
        seed: Optional[int] = 0,
    ) -> None:
        self.env = env
        self.species = species
        self.record_history = record_history
        self.history_stride = max(1, int(history_stride))
        self.rng = np.random.default_rng(seed)

        self.suitability: np.ndarray = habitat_suitability(env, species.niche)
        self._habitable: np.ndarray = self.suitability > 0.0
        self._kernel: np.ndarray = make_dispersal_kernel(env.grid, species.dispersal)
        self._norm_cache: Optional[np.ndarray] = None
        self._refresh_norm_cache()

        self.N: np.ndarray = np.zeros(env.grid.shape, dtype=np.float32)
        self.t: int = 0
        self.seed_rc: Optional[Tuple[int, int]] = None
        self._distance_from_seed: Optional[np.ndarray] = None

        self.history: List[np.ndarray] = []
        self.metrics: List[StepMetrics] = []

    # -- configuration ---------------------------------------------------- #
    def _refresh_norm_cache(self) -> None:
        if self.species.dispersal.boundary == "reflecting":
            self._norm_cache = _convolve(
                self._habitable.astype(np.float32), self._kernel
            )
        else:
            self._norm_cache = None

    def update_params(self, species: SpeciesParams) -> None:
        """Hot-swap parameters mid-run (the UI does this on every slider move).

        Recomputes suitability and the kernel, and extirpates any population
        sitting in cells that just became unsuitable.
        """
        niche_changed = species.niche != self.species.niche
        dispersal_changed = species.dispersal != self.species.dispersal
        self.species = species

        if niche_changed:
            self.suitability = habitat_suitability(self.env, species.niche)
            self._habitable = self.suitability > 0.0
            self.N = np.where(self._habitable, self.N, 0.0).astype(np.float32)
        if dispersal_changed:
            self._kernel = make_dispersal_kernel(self.env.grid, species.dispersal)
        if niche_changed or dispersal_changed:
            self._refresh_norm_cache()

    # -- state ------------------------------------------------------------ #
    def reset(self, keep_seed: bool = True) -> None:
        """Zero the population and history; optionally re-apply the last seed."""
        seed_rc, n0 = self.seed_rc, getattr(self, "_seed_n0", 0.0)
        radius = getattr(self, "_seed_radius", 0)
        self.N = np.zeros(self.env.grid.shape, dtype=np.float32)
        self.t = 0
        self.history.clear()
        self.metrics.clear()
        if keep_seed and seed_rc is not None:
            self.seed_rc = None
            self.seed_at(*seed_rc, n0=n0, radius_cells=radius)
        else:
            self.seed_rc = None
            self._distance_from_seed = None

    def seed_at(
        self,
        row: int,
        col: int,
        n0: float = 500.0,
        radius_cells: int = 0,
        additive: bool = True,
    ) -> bool:
        """Introduce ``n0`` individuals at a grid cell.

        Returns ``False`` (and does nothing) if the target cell is unsuitable,
        which is exactly what the UI wants to report back to the user.
        """
        if not (0 <= row < self.env.grid.n_rows and 0 <= col < self.env.grid.n_cols):
            return False
        if not self._habitable[row, col]:
            return False

        patch = np.zeros_like(self.N)
        if radius_cells <= 0:
            patch[row, col] = n0
        else:
            # Spread N0 evenly over the release disc, so the founding
            # population size is independent of the patch radius.
            rr, cc = np.indices(self.env.grid.shape)
            within = ((rr - row) ** 2 + (cc - col) ** 2) <= radius_cells**2
            within &= self._habitable
            n_cells = int(within.sum()) or 1
            patch = np.where(within, n0 / n_cells, 0.0).astype(np.float32)

        patch = patch * self._habitable
        self.N = (self.N + patch if additive else patch).astype(np.float32)

        self.seed_rc = (row, col)
        self._seed_n0 = n0
        self._seed_radius = radius_cells
        self._distance_from_seed = self.env.grid.distance_km_from(row, col)
        if self.record_history and not self.metrics:
            self._record()
        return True

    def seed(
        self,
        lon: float,
        lat: float,
        n0: float = 500.0,
        radius_cells: int = 0,
        additive: bool = True,
    ) -> bool:
        """Geographic-coordinate wrapper around :meth:`seed_at`."""
        rc = self.env.grid.lonlat_to_rc(lon, lat)
        if rc is None:
            return False
        return self.seed_at(*rc, n0=n0, radius_cells=radius_cells, additive=additive)

    # -- time stepping ---------------------------------------------------- #
    def _apply_jumps(self) -> None:
        """Rare stochastic long-distance dispersal (human-mediated jumps)."""
        d = self.species.dispersal
        if d.jump_probability <= 0.0:
            return
        sources = np.argwhere(self.N > 0.0)
        if sources.size == 0:
            return
        n_jumps = self.rng.binomial(len(sources), min(d.jump_probability, 1.0))
        if n_jumps == 0:
            return

        grid = self.env.grid
        picks = sources[self.rng.integers(0, len(sources), size=n_jumps)]
        angles = self.rng.uniform(0.0, 2.0 * np.pi, size=n_jumps)
        dists = self.rng.exponential(d.jump_distance_km, size=n_jumps)
        d_rows = np.rint(dists * np.sin(angles) / grid.cell_height_km).astype(int)
        d_cols = np.rint(dists * np.cos(angles) / grid.cell_width_km).astype(int)

        for (r0, c0), dr, dc in zip(picks, d_rows, d_cols):
            r, c = r0 + dr, c0 + dc
            if not (0 <= r < grid.n_rows and 0 <= c < grid.n_cols):
                continue
            if not self._habitable[r, c]:
                continue
            emigrants = 0.05 * self.N[r0, c0]
            self.N[r0, c0] -= emigrants
            self.N[r, c] += emigrants

    def step(self) -> StepMetrics:
        """Advance the simulation by one time step and return its metrics."""
        self.N = logistic_step(self.N, self.suitability, self.species.demography)
        self.N = disperse(
            self.N,
            self._kernel,
            self._habitable,
            self.species.dispersal,
            _norm_cache=self._norm_cache,
        )
        self._apply_jumps()
        self.N = np.where(
            self.N < self.species.demography.extinction_floor, 0.0, self.N
        ).astype(np.float32)
        self.t += 1
        return self._record()

    def run(self, n_steps: int, callback: Optional[Callable[[int], None]] = None) -> None:
        """Advance ``n_steps`` steps, optionally calling ``callback(t)`` each one."""
        for _ in range(int(n_steps)):
            self.step()
            if callback is not None:
                callback(self.t)

    # -- diagnostics ------------------------------------------------------ #
    def _record(self) -> StepMetrics:
        occupied = self.N > 0.0
        n_occ = int(occupied.sum())
        total = float(self.N.sum())

        if self._distance_from_seed is not None and n_occ:
            front = float(self._distance_from_seed[occupied].max())
        else:
            front = 0.0
        prev_front = self.metrics[-1].front_km if self.metrics else 0.0

        m = StepMetrics(
            step=self.t,
            total_population=total,
            occupied_cells=n_occ,
            occupied_area_km2=n_occ * self.env.grid.cell_area_km2,
            mean_density=total / n_occ if n_occ else 0.0,
            front_km=front,
            frontier_speed_km=front - prev_front,
        )
        self.metrics.append(m)
        if self.record_history and (self.t % self.history_stride == 0):
            self.history.append(self.N.copy())
        return m

    # -- convenience for the UI ------------------------------------------- #
    @property
    def carrying_capacity(self) -> np.ndarray:
        return self.species.demography.K * self.suitability

    def occupancy_fraction(self) -> float:
        habitable = int(self._habitable.sum())
        return float((self.N > 0).sum()) / habitable if habitable else 0.0

    def metrics_table(self) -> List[Dict[str, float]]:
        return [m.as_dict() for m in self.metrics]

    def frame(self, index: int = -1) -> np.ndarray:
        """Return a recorded population field (``-1`` = current state)."""
        if index == -1 or not self.history:
            return self.N
        return self.history[max(0, min(index, len(self.history) - 1))]

    def summary(self) -> str:
        m = self.metrics[-1] if self.metrics else None
        if m is None:
            return "not started"
        return (
            f"t={m.step}  N={m.total_population:,.0f}  "
            f"cells={m.occupied_cells}  front={m.front_km:,.0f} km"
        )
