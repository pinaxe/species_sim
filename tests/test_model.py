"""
Unit tests for the simulation engine.

These are behavioural rather than golden-value tests: they pin down the
properties the model is *supposed* to have (mass conservation, logistic
equilibrium, kernel normalisation, monotone spread) so refactors that break
the ecology fail loudly.

Run with::

    pytest -q
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import synthetic_environment  # noqa: E402
from model import (  # noqa: E402
    DemographyParams,
    DispersalParams,
    Environment,
    GridSpec,
    NicheParams,
    Simulator,
    SpeciesParams,
    disperse,
    gaussian_response,
    habitat_suitability,
    logistic_step,
    make_dispersal_kernel,
)


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture
def grid() -> GridSpec:
    return GridSpec(west=-124.0, south=44.0, east=-120.0, north=48.0,
                    n_rows=60, n_cols=60)


@pytest.fixture
def flat_env(grid: GridSpec) -> Environment:
    """A perfectly uniform, all-land world -- analytically tractable."""
    return Environment(
        grid=grid,
        temperature=np.full(grid.shape, 18.0, dtype=np.float32),
        precipitation=np.full(grid.shape, 1000.0, dtype=np.float32),
        land_mask=np.ones(grid.shape, dtype=bool),
        name="flat",
    )


# --------------------------------------------------------------------------- #
# Grid geometry
# --------------------------------------------------------------------------- #
def test_grid_roundtrip(grid: GridSpec):
    for rc in [(0, 0), (17, 43), (59, 59)]:
        lon, lat = grid.rc_to_lonlat(*rc)
        assert grid.lonlat_to_rc(lon, lat) == rc


def test_grid_orientation(grid: GridSpec):
    assert grid.lats[0] > grid.lats[-1], "row 0 must be the north edge"
    assert grid.lons[0] < grid.lons[-1]


def test_cell_size_positive(grid: GridSpec):
    assert grid.cell_width_km > 0 and grid.cell_height_km > 0
    # ~0.0667 deg at 46 deg N: height ~7.4 km, width ~5.1 km
    assert 6.0 < grid.cell_height_km < 9.0
    assert grid.cell_width_km < grid.cell_height_km


def test_out_of_bounds_returns_none(grid: GridSpec):
    assert grid.lonlat_to_rc(0.0, 0.0) is None


# --------------------------------------------------------------------------- #
# Niche
# --------------------------------------------------------------------------- #
def test_gaussian_response_peaks_at_optimum():
    assert np.isclose(gaussian_response(np.array([18.0]), 18.0, 5.0)[0], 1.0, atol=1e-6)
    x = np.linspace(-10, 40, 501)
    y = gaussian_response(x, opt=18.0, tol=5.0)
    assert y.max() <= 1.0 + 1e-6
    assert abs(x[np.argmax(y)] - 18.0) <= (x[1] - x[0])
    # One sigma away the response must be exp(-0.5)
    assert np.isclose(gaussian_response(np.array([23.0]), 18.0, 5.0)[0],
                      np.exp(-0.5), atol=1e-5)


def test_suitability_bounds_and_mask(flat_env: Environment):
    niche = NicheParams(t_opt=18.0, t_tol=5.0, p_opt=1000.0, p_tol=500.0)
    s = habitat_suitability(flat_env, niche)
    assert s.min() >= 0.0 and s.max() <= 1.0
    assert np.allclose(s, 1.0, atol=1e-5), "uniform optimal world => S == 1"

    flat_env.land_mask[:10, :] = False
    s2 = habitat_suitability(flat_env, niche)
    assert np.all(s2[:10, :] == 0.0)


def test_specialist_has_smaller_range_than_generalist(grid: GridSpec):
    env = synthetic_environment(grid, seed=7)
    specialist = habitat_suitability(env, NicheParams(t_opt=15.0, t_tol=1.5))
    generalist = habitat_suitability(env, NicheParams(t_opt=15.0, t_tol=12.0))
    assert (specialist > 0).sum() < (generalist > 0).sum()


# --------------------------------------------------------------------------- #
# Logistic growth
# --------------------------------------------------------------------------- #
def test_logistic_converges_to_capacity():
    demo = DemographyParams(r=0.3, K=1000.0, mortality=0.0, allee_threshold=0.0)
    S = np.ones((4, 4), dtype=np.float32)
    N = np.full((4, 4), 1.0, dtype=np.float32)
    for _ in range(400):
        N = logistic_step(N, S, demo)
    assert np.allclose(N, 1000.0, rtol=1e-3)


def test_mortality_lowers_equilibrium():
    S = np.ones((3, 3), dtype=np.float32)
    eq = {}
    for m in (0.0, 0.1):
        demo = DemographyParams(r=0.4, K=1000.0, mortality=m)
        N = np.full((3, 3), 10.0, dtype=np.float32)
        for _ in range(600):
            N = logistic_step(N, S, demo)
        eq[m] = float(N.mean())
    # Analytic equilibrium of N + rN(1-N/K) - mN = N  ->  N* = K(1 - m/r)
    assert np.isclose(eq[0.1], 1000.0 * (1 - 0.1 / 0.4), rtol=1e-2)
    assert eq[0.1] < eq[0.0]


def test_mortality_above_r_causes_extinction():
    demo = DemographyParams(r=0.1, K=1000.0, mortality=0.3)
    S = np.ones((3, 3), dtype=np.float32)
    N = np.full((3, 3), 500.0, dtype=np.float32)
    for _ in range(500):
        N = logistic_step(N, S, demo)
    assert N.sum() == 0.0


def test_zero_suitability_extirpates():
    demo = DemographyParams(r=0.5, K=1000.0, mortality=0.0)
    S = np.zeros((3, 3), dtype=np.float32)
    N = logistic_step(np.full((3, 3), 100.0, dtype=np.float32), S, demo)
    assert N.sum() == 0.0


def test_population_never_negative():
    demo = DemographyParams(r=1.9, K=100.0, mortality=0.5)
    S = np.ones((5, 5), dtype=np.float32)
    N = np.full((5, 5), 95.0, dtype=np.float32)
    for _ in range(200):
        N = logistic_step(N, S, demo)
        assert (N >= 0).all()


def test_capacity_scales_with_suitability():
    demo = DemographyParams(r=0.4, K=1000.0, mortality=0.0)
    S = np.array([[1.0, 0.5, 0.25]], dtype=np.float32)
    N = np.full((1, 3), 1.0, dtype=np.float32)
    for _ in range(400):
        N = logistic_step(N, S, demo)
    assert np.allclose(N[0], [1000.0, 500.0, 250.0], rtol=1e-3)


# --------------------------------------------------------------------------- #
# Dispersal kernel
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("kernel", ["gaussian", "exponential", "fat_tail"])
def test_kernel_normalised_and_symmetric(grid: GridSpec, kernel: str):
    k = make_dispersal_kernel(grid, DispersalParams(sigma_km=20.0, kernel=kernel))
    assert np.isclose(k.sum(), 1.0, atol=1e-5)
    assert k.shape[0] % 2 == 1 and k.shape[1] % 2 == 1
    assert np.allclose(k, k[::-1, :], atol=1e-6)
    assert np.allclose(k, k[:, ::-1], atol=1e-6)
    assert k.argmax() == k.size // 2, "kernel must peak at the source cell"


def test_kernel_grows_with_sigma(grid: GridSpec):
    small = make_dispersal_kernel(grid, DispersalParams(sigma_km=5.0))
    large = make_dispersal_kernel(grid, DispersalParams(sigma_km=60.0))
    assert large.size > small.size


def test_kernel_is_anisotropic_in_index_space(grid: GridSpec):
    """Cells are wider N-S than E-W here, so the kernel must be wider in x."""
    k = make_dispersal_kernel(grid, DispersalParams(sigma_km=30.0))
    assert k.shape[1] > k.shape[0]


def test_fat_tail_has_heavier_tail_than_gaussian(grid: GridSpec):
    g = make_dispersal_kernel(grid, DispersalParams(sigma_km=20.0, kernel="gaussian"))
    f = make_dispersal_kernel(grid, DispersalParams(sigma_km=20.0, kernel="fat_tail"))
    # Compare the weight in the outermost ring of the *smaller* kernel's support.
    assert f[0, f.shape[1] // 2] > g[0, g.shape[1] // 2]


# --------------------------------------------------------------------------- #
# Dispersal operator
# --------------------------------------------------------------------------- #
def test_reflecting_dispersal_conserves_mass(grid: GridSpec):
    params = DispersalParams(sigma_km=25.0, fraction=0.5, boundary="reflecting")
    k = make_dispersal_kernel(grid, params)
    habitable = np.ones(grid.shape, dtype=bool)
    habitable[:, :10] = False  # a "coastline"
    N = np.zeros(grid.shape, dtype=np.float32)
    N[30, 30] = 1000.0
    before = N.sum()
    for _ in range(20):
        N = disperse(N, k, habitable, params)
    assert np.isclose(N.sum(), before, rtol=1e-3)
    assert N[habitable == False].sum() == 0.0  # noqa: E712


def test_absorbing_dispersal_loses_mass_at_the_edge(grid: GridSpec):
    params = DispersalParams(sigma_km=40.0, fraction=1.0, boundary="absorbing")
    k = make_dispersal_kernel(grid, params)
    habitable = np.ones(grid.shape, dtype=bool)
    N = np.zeros(grid.shape, dtype=np.float32)
    N[1, 1] = 1000.0  # right against the corner
    out = disperse(N, k, habitable, params)
    assert out.sum() < N.sum()


def test_dispersal_spreads_and_zero_fraction_does_not(grid: GridSpec):
    habitable = np.ones(grid.shape, dtype=bool)
    N = np.zeros(grid.shape, dtype=np.float32)
    N[30, 30] = 1000.0

    moving = DispersalParams(sigma_km=25.0, fraction=0.4)
    k = make_dispersal_kernel(grid, moving)
    assert (disperse(N, k, habitable, moving) > 0).sum() > 1

    still = DispersalParams(sigma_km=25.0, fraction=0.0)
    assert np.array_equal(disperse(N, k, habitable, still), N)


# --------------------------------------------------------------------------- #
# Simulator integration
# --------------------------------------------------------------------------- #
def test_seed_and_spread(flat_env: Environment):
    sim = Simulator(flat_env, SpeciesParams(), seed=1)
    assert sim.seed(lon=-122.0, lat=46.0, n0=500.0)
    start_cells = int((sim.N > 0).sum())
    sim.run(25)
    assert int((sim.N > 0).sum()) > start_cells
    assert sim.metrics[-1].total_population > 500.0
    assert sim.metrics[-1].front_km > 0.0


def test_front_distance_is_monotone(flat_env: Environment):
    sim = Simulator(flat_env, SpeciesParams(), seed=1)
    sim.seed(lon=-122.0, lat=46.0, n0=500.0)
    sim.run(30)
    fronts = [m.front_km for m in sim.metrics]
    assert all(b >= a - 1e-6 for a, b in zip(fronts, fronts[1:]))


def test_seed_rejects_unsuitable_cell(flat_env: Environment):
    flat_env.land_mask[:] = False
    flat_env.land_mask[0, 0] = True
    sim = Simulator(flat_env, SpeciesParams(), seed=1)
    assert sim.seed(lon=-122.0, lat=46.0, n0=500.0) is False
    assert sim.N.sum() == 0.0


def test_reset_restores_initial_state(flat_env: Environment):
    sim = Simulator(flat_env, SpeciesParams(), seed=1)
    sim.seed(lon=-122.0, lat=46.0, n0=500.0, radius_cells=2)
    initial = sim.N.copy()
    sim.run(15)
    assert not np.array_equal(sim.N, initial)

    sim.reset(keep_seed=True)
    assert sim.t == 0
    assert sim.seed_rc is not None
    assert len(sim.metrics) == 1
    assert np.allclose(sim.N, initial), "reset must reproduce the release patch"
    assert np.isclose(sim.N.sum(), 500.0, rtol=1e-4)

    sim.reset(keep_seed=False)
    assert sim.N.sum() == 0.0 and sim.seed_rc is None


def test_release_patch_size_is_independent_of_radius(flat_env: Environment):
    totals = []
    for radius in (0, 1, 3):
        sim = Simulator(flat_env, SpeciesParams(), seed=1)
        sim.seed(lon=-122.0, lat=46.0, n0=500.0, radius_cells=radius)
        totals.append(float(sim.N.sum()))
    assert np.allclose(totals, 500.0, rtol=1e-4)


def test_update_params_extirpates_newly_unsuitable_cells(flat_env: Environment):
    sim = Simulator(flat_env, SpeciesParams(), seed=1)
    sim.seed(lon=-122.0, lat=46.0, n0=500.0)
    sim.run(10)
    assert sim.N.sum() > 0
    # Shift the thermal optimum far away from the (uniform 18 degC) world.
    hostile = SpeciesParams(niche=NicheParams(t_opt=-40.0, t_tol=1.0))
    sim.update_params(hostile)
    assert sim.N.sum() == 0.0


def test_no_growth_without_seed(flat_env: Environment):
    sim = Simulator(flat_env, SpeciesParams(), seed=1)
    sim.run(20)
    assert sim.N.sum() == 0.0


def test_allee_effect_can_prevent_establishment(flat_env: Environment):
    species = SpeciesParams(
        demography=DemographyParams(r=0.3, K=1000.0, mortality=0.05,
                                    allee_threshold=200.0),
        dispersal=DispersalParams(sigma_km=60.0, fraction=0.9),
    )
    sim = Simulator(flat_env, species, seed=1)
    sim.seed(lon=-122.0, lat=46.0, n0=50.0)
    sim.run(20)
    assert sim.metrics[-1].total_population == 0.0


def test_metrics_table_shape(flat_env: Environment):
    sim = Simulator(flat_env, SpeciesParams(), seed=1)
    sim.seed(lon=-122.0, lat=46.0, n0=500.0)
    sim.run(5)
    table = sim.metrics_table()
    assert len(table) == 6  # t=0 record plus 5 steps
    assert table[-1]["step"] == 5


def test_faster_dispersal_gives_a_faster_front(flat_env: Environment):
    fronts = {}
    for sigma in (8.0, 45.0):
        species = SpeciesParams(dispersal=DispersalParams(sigma_km=sigma, fraction=0.3))
        sim = Simulator(flat_env, species, seed=1)
        sim.seed(lon=-122.0, lat=46.0, n0=500.0)
        sim.run(20)
        fronts[sigma] = sim.metrics[-1].front_km
    assert fronts[45.0] > fronts[8.0]


def test_synthetic_environment_is_deterministic(grid: GridSpec):
    a = synthetic_environment(grid, seed=11)
    b = synthetic_environment(grid, seed=11)
    assert np.array_equal(a.temperature, b.temperature)
    assert np.array_equal(a.land_mask, b.land_mask)
    c = synthetic_environment(grid, seed=12)
    assert not np.array_equal(a.temperature, c.temperature)


def test_synthetic_environment_is_physically_plausible(grid: GridSpec):
    env = synthetic_environment(grid, seed=3)
    land = env.land_mask
    assert -40.0 < env.temperature[land].mean() < 40.0
    assert 30.0 <= env.precipitation.min()
    assert 0.2 < land.mean() < 0.95
