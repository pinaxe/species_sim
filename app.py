"""
app.py
======

Streamlit front end for the Species Distribution & Dispersal Simulator.

Run with::

    streamlit run app.py

Workflow
--------
1. Pick a region and a species preset in the sidebar.
2. Click anywhere on the **Seed on map** view to introduce the founding
   population. Unsuitable cells (ocean, outside the niche) refuse the seed and
   say so.
3. Switch to **Simulation view** and press Play. The heatmap is the population
   density; the charts below track total abundance, occupied area and the
   distance the invasion front has travelled from the release point.

Layout notes: every widget writes into ``st.session_state`` and the simulator
object itself is the single source of truth, so a slider moved mid-run updates
the live simulation instead of restarting it. Only the *grid* is expensive to
rebuild, so it is cached separately.
"""

from __future__ import annotations

import base64
import io
import time
from dataclasses import replace
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st

from data import REGIONS, discover_rasters, fit_niche_from_occurrences, gbif_occurrences, load_environment
from model import (
    DemographyParams,
    DispersalParams,
    Environment,
    NicheParams,
    Simulator,
    SpeciesParams,
    habitat_suitability,
)
from species import get_preset, preset_names

st.set_page_config(
    page_title="Species Introduction Simulator",
    page_icon="🌱",
    layout="wide",
)

# --------------------------------------------------------------------------- #
# Optional dependencies -- the app degrades instead of crashing
# --------------------------------------------------------------------------- #
try:
    import pydeck as pdk

    HAS_PYDECK = True
except Exception:  # pragma: no cover
    HAS_PYDECK = False

try:
    import folium
    from streamlit_folium import st_folium

    HAS_FOLIUM = True
except Exception:  # pragma: no cover
    HAS_FOLIUM = False


# --------------------------------------------------------------------------- #
# Raster -> PNG data URI
# --------------------------------------------------------------------------- #
def array_to_png_uri(
    values: np.ndarray,
    cmap_name: str = "inferno",
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    alpha_gamma: float = 0.6,
    mask: Optional[np.ndarray] = None,
    opaque: bool = False,
) -> str:
    """Colour-map a 2D array into a base64 PNG data URI.

    Alpha is driven by the (gamma-corrected) normalised value so low densities
    fade out and the basemap shows through -- which is what makes an invasion
    wavefront legible rather than a solid blob.
    """
    import matplotlib
    from matplotlib.colors import Normalize
    from PIL import Image

    try:  # matplotlib >= 3.6
        cmap = matplotlib.colormaps[cmap_name]
    except Exception:  # pragma: no cover - older matplotlib
        from matplotlib import cm

        cmap = cm.get_cmap(cmap_name)

    arr = np.asarray(values, dtype=np.float32)
    finite = arr[np.isfinite(arr)]
    lo = float(vmin) if vmin is not None else (float(finite.min()) if finite.size else 0.0)
    hi = float(vmax) if vmax is not None else (float(finite.max()) if finite.size else 1.0)
    if hi <= lo:
        hi = lo + 1e-6

    norm = Normalize(vmin=lo, vmax=hi, clip=True)
    scaled = norm(np.nan_to_num(arr, nan=lo))
    rgba = (cmap(scaled) * 255).astype(np.uint8)

    if opaque:
        alpha = np.full(arr.shape, 255, dtype=np.uint8)
    else:
        alpha = (np.clip(scaled, 0, 1) ** alpha_gamma * 255).astype(np.uint8)
    if mask is not None:
        alpha = np.where(mask, alpha, 0).astype(np.uint8)
    rgba[..., 3] = alpha

    buf = io.BytesIO()
    Image.fromarray(rgba, mode="RGBA").save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


# --------------------------------------------------------------------------- #
# Cached environment construction
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner="Building environmental grid…")
def build_environment(
    region: str,
    resolution_deg: float,
    seed: int,
    temperature_path: Optional[str],
    precipitation_path: Optional[str],
    temperature_scale: float,
) -> Environment:
    return load_environment(
        region=region,
        resolution_deg=resolution_deg,
        temperature_path=temperature_path,
        precipitation_path=precipitation_path,
        temperature_scale=temperature_scale,
        seed=seed,
    )


# --------------------------------------------------------------------------- #
# Sidebar -- configuration
# --------------------------------------------------------------------------- #
def sidebar_controls() -> Tuple[Environment, SpeciesParams, dict]:
    st.sidebar.title("🌱 Simulator controls")

    # ---- Landscape ------------------------------------------------------ #
    with st.sidebar.expander("🗺️  Landscape", expanded=True):
        region = st.selectbox("Region", list(REGIONS.keys()), index=0)
        preset_region = REGIONS[region]
        resolution = st.select_slider(
            "Grid resolution (degrees)",
            options=[0.05, 0.08, 0.1, 0.15, 0.2, 0.25, 0.5, 1.0],
            value=float(preset_region.resolution_deg),
            help="Finer grids resolve the front better but cost O(n²) per step.",
        )
        rasters = discover_rasters()
        if rasters:
            options = ["Synthetic climate"] + list(rasters.keys())
            t_choice = st.selectbox("Temperature layer", options, index=0)
            p_choice = st.selectbox("Precipitation layer", options, index=0)
            t_path = rasters.get(t_choice)
            p_path = rasters.get(p_choice)
            t_scale = st.number_input(
                "Temperature scale factor",
                value=1.0,
                help="WorldClim v1 stores °C×10 → use 0.1. WorldClim v2 → 1.0.",
            )
        else:
            st.caption(
                "No GeoTIFFs found in `data/`. Using a procedural climate. "
                "Drop WorldClim `bio1`/`bio12` tiles in `data/` to use real rasters."
            )
            t_path = p_path = None
            t_scale = 1.0
        landscape_seed = st.number_input("Landscape random seed", 0, 9999, 42, step=1)

    env = build_environment(region, float(resolution), int(landscape_seed), t_path, p_path, float(t_scale))
    grid = env.grid
    st.sidebar.caption(
        f"Grid **{grid.n_rows}×{grid.n_cols}** · cell ≈ "
        f"{grid.cell_width_km:.1f}×{grid.cell_height_km:.1f} km · "
        f"{int(env.land_mask.sum()):,} land cells"
    )

    # ---- Species -------------------------------------------------------- #
    with st.sidebar.expander("🦋  Species", expanded=True):
        preset_name = st.selectbox("Preset", preset_names(), index=0)
        if st.session_state.get("_preset_name") != preset_name:
            st.session_state["_preset_name"] = preset_name
            st.session_state["_preset"] = get_preset(preset_name)
            st.session_state["_param_rev"] = st.session_state.get("_param_rev", 0) + 1
            st.rerun()
        base: SpeciesParams = st.session_state.get("_preset") or get_preset(preset_name)
        st.caption(base.notes)

    # Widget keys embed the preset name and a revision counter, so switching
    # preset (or fitting a niche from GBIF) genuinely resets the sliders
    # instead of leaving stale values behind.
    rev = st.session_state.get("_param_rev", 0)
    kk = lambda field: f"{field}::{preset_name}::{rev}"  # noqa: E731

    # ---- Niche ---------------------------------------------------------- #
    with st.sidebar.expander("🌡️  Niche (habitat suitability)", expanded=True):
        t_opt = st.slider("Thermal optimum  Tₒₚₜ (°C)", -20.0, 40.0,
                          float(np.clip(base.niche.t_opt, -20.0, 40.0)), 0.5, key=kk("t_opt"))
        t_tol = st.slider("Thermal tolerance  σ_T (°C)", 0.5, 20.0,
                          float(np.clip(base.niche.t_tol, 0.5, 20.0)), 0.5, key=kk("t_tol"),
                          help="Standard deviation of the Gaussian tolerance curve. "
                               "Small σ = specialist.")
        use_precip = st.checkbox("Include precipitation axis",
                                 value=base.niche.use_precipitation, key=kk("use_p"))
        p_opt = st.slider("Precipitation optimum (mm/yr)", 0.0, 4000.0,
                          float(np.clip(base.niche.p_opt, 0.0, 4000.0)), 25.0,
                          disabled=not use_precip, key=kk("p_opt"))
        p_tol = st.slider("Precipitation tolerance σ_P (mm/yr)", 25.0, 2500.0,
                          float(np.clip(base.niche.p_tol, 25.0, 2500.0)), 25.0,
                          disabled=not use_precip, key=kk("p_tol"))
        niche = NicheParams(
            t_opt=t_opt, t_tol=t_tol, p_opt=p_opt, p_tol=p_tol,
            use_precipitation=use_precip,
            suitability_floor=base.niche.suitability_floor,
        )

    # ---- Demography ------------------------------------------------------ #
    with st.sidebar.expander("📈  Population dynamics", expanded=True):
        r = st.slider("Intrinsic growth rate  r", 0.0, 2.0,
                      float(base.demography.r), 0.01, key=kk("r"))
        K = st.slider("Carrying capacity  K (per ideal cell)", 50.0, 10000.0,
                      float(base.demography.K), 50.0, key=kk("K"))
        mortality = st.slider("Mortality  m (per step)", 0.0, 0.6,
                              float(base.demography.mortality), 0.01, key=kk("m"))
        allee = st.slider("Allee threshold (individuals/cell)", 0.0, 50.0,
                          float(base.demography.allee_threshold), 1.0, key=kk("allee"),
                          help="Cells below this density go extinct — small "
                               "founder patches can fail to establish.")
        demography = DemographyParams(
            r=r, K=K, mortality=mortality, allee_threshold=allee,
            extinction_floor=base.demography.extinction_floor,
        )
        if r > 2.0 - 1e-9:
            st.warning("r > 2 makes the discrete logistic map chaotic.")

    # ---- Dispersal ------------------------------------------------------- #
    with st.sidebar.expander("💨  Dispersal", expanded=True):
        kernel = st.selectbox(
            "Kernel shape", ["gaussian", "exponential", "fat_tail"],
            index=["gaussian", "exponential", "fat_tail"].index(base.dispersal.kernel),
            key=kk("kernel"),
            help="Gaussian = diffusive wave · exponential = leptokurtic · "
                 "fat_tail = power law, accelerating spread.",
        )
        sigma_km = st.slider("Dispersal radius  σ (km)", 1.0, 200.0,
                             float(base.dispersal.sigma_km), 1.0, key=kk("sigma"))
        fraction = st.slider("Dispersing fraction per step", 0.0, 1.0,
                             float(base.dispersal.fraction), 0.01, key=kk("frac"))
        boundary = st.radio("Boundary / coastline", ["reflecting", "absorbing"],
                            index=0 if base.dispersal.boundary == "reflecting" else 1,
                            horizontal=True, key=kk("boundary"),
                            help="Reflecting conserves population exactly; "
                                 "absorbing lets propagules die at sea.")
        jump_p = st.slider("Long-distance jump probability", 0.0, 0.2,
                           float(base.dispersal.jump_probability), 0.005, key=kk("jump_p"),
                           help="Human-mediated stratified diffusion. >0 makes "
                                "runs stochastic.")
        jump_km = st.slider("Mean jump distance (km)", 50.0, 2000.0,
                            float(base.dispersal.jump_distance_km), 25.0,
                            disabled=jump_p <= 0, key=kk("jump_km"))
        dispersal = DispersalParams(
            sigma_km=sigma_km, kernel=kernel, fraction=fraction,
            truncate=base.dispersal.truncate, boundary=boundary,
            jump_probability=jump_p, jump_distance_km=jump_km,
            fat_tail_alpha=base.dispersal.fat_tail_alpha,
        )

    # ---- Introduction & playback ----------------------------------------- #
    with st.sidebar.expander("🎯  Introduction & playback", expanded=True):
        n0 = st.number_input("Founding population N₀", 1.0, 1e6, 500.0, step=50.0,
                             key="ui_n0")
        seed_radius = st.slider("Release patch radius (cells)", 0, 8, 1, key="ui_radius")
        max_steps = st.slider("Simulation length (steps)", 10, 500, 120, 10, key="ui_steps")
        fps = st.slider("Playback speed (steps/sec)", 1, 30, 8, key="ui_fps")

    ui = dict(n0=n0, seed_radius=seed_radius, max_steps=max_steps, fps=fps,
              region=region, resolution=resolution)
    species = SpeciesParams(
        name=preset_name, niche=niche, demography=demography,
        dispersal=dispersal, notes=base.notes,
    )
    return env, species, ui


# --------------------------------------------------------------------------- #
# Simulator lifecycle
# --------------------------------------------------------------------------- #
def get_simulator(env: Environment, species: SpeciesParams) -> Simulator:
    signature = (env.name, env.grid.shape, env.grid.bounds)
    if st.session_state.get("_env_signature") != signature:
        st.session_state["_env_signature"] = signature
        st.session_state["sim"] = Simulator(env, species, history_stride=1)
        st.session_state["playing"] = False
    sim: Simulator = st.session_state["sim"]
    sim.update_params(species)
    return sim


# --------------------------------------------------------------------------- #
# Map views
# --------------------------------------------------------------------------- #
def seeding_map(sim: Simulator, ui: dict) -> None:
    """Folium map: click anywhere to release the founding population."""
    grid = sim.env.grid
    lat0, lon0 = (grid.mean_lat, 0.5 * (grid.west + grid.east))

    if not HAS_FOLIUM:
        st.warning("`streamlit-folium` is not installed — use the coordinate boxes below.")
    else:
        suit_uri = array_to_png_uri(
            sim.suitability, cmap_name="YlGn", vmin=0.0, vmax=1.0,
            alpha_gamma=0.5, mask=sim.env.land_mask,
        )
        m = folium.Map(location=[lat0, lon0], zoom_start=5, tiles="CartoDB positron")
        folium.raster_layers.ImageOverlay(
            image=suit_uri,
            bounds=[[grid.south, grid.west], [grid.north, grid.east]],
            opacity=0.65, name="Habitat suitability", interactive=False,
        ).add_to(m)
        if sim.N.max() > 0:
            pop_uri = array_to_png_uri(
                sim.N, cmap_name="inferno", vmin=0.0,
                vmax=float(max(sim.N.max(), 1e-6)), mask=sim.N > 0,
            )
            folium.raster_layers.ImageOverlay(
                image=pop_uri,
                bounds=[[grid.south, grid.west], [grid.north, grid.east]],
                opacity=0.85, name="Population", interactive=False,
            ).add_to(m)
        if sim.seed_rc is not None:
            slon, slat = grid.rc_to_lonlat(*sim.seed_rc)
            folium.CircleMarker([slat, slon], radius=6, color="#ff2d55",
                                fill=True, fill_opacity=1.0,
                                tooltip="Introduction point").add_to(m)
        for lon, lat in st.session_state.get("gbif_points", ())[:400]:
            folium.CircleMarker([lat, lon], radius=2, color="#1f6feb",
                                fill=True, fill_opacity=0.7, weight=0).add_to(m)
        folium.LayerControl(collapsed=True).add_to(m)
        folium.Rectangle([[grid.south, grid.west], [grid.north, grid.east]],
                         color="#555", weight=1, fill=False).add_to(m)

        out = st_folium(m, height=560, use_container_width=True,
                        returned_objects=["last_clicked"], key="seed_map")
        clicked = (out or {}).get("last_clicked")
        if clicked:
            key = (round(clicked["lat"], 6), round(clicked["lng"], 6))
            if st.session_state.get("_last_click") != key:
                st.session_state["_last_click"] = key
                ok = sim.seed(clicked["lng"], clicked["lat"],
                              n0=ui["n0"], radius_cells=ui["seed_radius"])
                st.session_state["_seed_message"] = (
                    ("success", f"Released {ui['n0']:,.0f} individuals at "
                                f"{clicked['lat']:.3f}°, {clicked['lng']:.3f}°.")
                    if ok else
                    ("error", "That cell is unsuitable (ocean, or outside the "
                              "species' niche). Try somewhere greener.")
                )
                st.rerun()

    msg = st.session_state.get("_seed_message")
    if msg:
        (st.success if msg[0] == "success" else st.error)(msg[1])

    with st.expander("…or enter coordinates directly"):
        c1, c2, c3 = st.columns([1, 1, 1])
        lon = c1.number_input("Longitude", grid.west, grid.east, float(lon0), 0.1)
        lat = c2.number_input("Latitude", grid.south, grid.north, float(lat0), 0.1)
        c3.write("")
        if c3.button("Release here", use_container_width=True):
            ok = sim.seed(lon, lat, n0=ui["n0"], radius_cells=ui["seed_radius"])
            st.session_state["_seed_message"] = (
                ("success", f"Released at {lat:.3f}°, {lon:.3f}°.") if ok
                else ("error", "Unsuitable cell — pick another point.")
            )
            st.rerun()


def simulation_map(sim: Simulator, layer_choice: str, show_suitability: bool) -> None:
    """PyDeck bitmap overlay of the live population field."""
    grid = sim.env.grid
    bounds = [grid.west, grid.south, grid.east, grid.north]

    if layer_choice == "Population density":
        field = sim.N
        vmax = float(max(sim.carrying_capacity.max(), 1e-6))
        uri = array_to_png_uri(field, "inferno", 0.0, vmax, mask=field > 0)
    elif layer_choice == "Occupancy (presence)":
        field = (sim.N > 0).astype(np.float32)
        uri = array_to_png_uri(field, "autumn", 0.0, 1.0, alpha_gamma=1.0, mask=field > 0)
    else:  # relative saturation N / (K·S)
        cap = sim.carrying_capacity
        field = np.divide(sim.N, cap, out=np.zeros_like(sim.N), where=cap > 0)
        uri = array_to_png_uri(field, "magma", 0.0, 1.0, mask=field > 0)

    if not HAS_PYDECK:
        st.warning("`pydeck` is not installed — showing a plain image instead.")
        st.image(uri, use_container_width=True)
        return

    layers = []
    if show_suitability:
        layers.append(
            pdk.Layer(
                "BitmapLayer",
                data=None,
                image=array_to_png_uri(sim.suitability, "YlGn", 0.0, 1.0,
                                       alpha_gamma=0.5, mask=sim.env.land_mask),
                bounds=bounds, opacity=0.45,
            )
        )
    layers.append(
        pdk.Layer("BitmapLayer", data=None, image=uri, bounds=bounds, opacity=0.9)
    )
    if sim.seed_rc is not None:
        slon, slat = grid.rc_to_lonlat(*sim.seed_rc)
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=[{"position": [slon, slat]}],
                get_position="position",
                get_fill_color=[255, 45, 85, 230],
                get_radius=6, radius_units="pixels", pickable=False,
            )
        )
    points = st.session_state.get("gbif_points", ())
    if points:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=[{"position": [lo, la]} for lo, la in points[:2000]],
                get_position="position",
                get_fill_color=[31, 111, 235, 160],
                get_radius=3, radius_units="pixels",
            )
        )

    view = pdk.ViewState(latitude=grid.mean_lat,
                         longitude=0.5 * (grid.west + grid.east),
                         zoom=4.2, bearing=0, pitch=0)
    st.pydeck_chart(
        pdk.Deck(layers=layers, initial_view_state=view,
                 map_style="light", tooltip=False),
        use_container_width=True,
    )


# --------------------------------------------------------------------------- #
# Charts & readouts
# --------------------------------------------------------------------------- #
def metrics_panel(sim: Simulator, ui: dict) -> None:
    if not sim.metrics:
        st.info("Release a population on the map to begin.")
        return

    m = sim.metrics[-1]
    c1, c2 = st.columns(2)
    c1.metric("Step", f"{m.step}", help="Time steps elapsed since introduction.")
    c2.metric("Total population", f"{m.total_population:,.0f}")
    c3, c4 = st.columns(2)
    c3.metric("Occupied area", f"{m.occupied_area_km2:,.0f} km²",
              delta=f"{(m.occupied_area_km2 - sim.metrics[-2].occupied_area_km2):,.0f}"
              if len(sim.metrics) > 1 else None)
    c4.metric("Front distance", f"{m.front_km:,.0f} km",
              delta=f"{m.frontier_speed_km:,.1f} km/step" if m.frontier_speed_km else None)
    st.progress(min(1.0, sim.occupancy_fraction()),
                text=f"{sim.occupancy_fraction():.1%} of habitable cells occupied")

    df = pd.DataFrame(sim.metrics_table()).set_index("step")
    st.caption("Total population")
    st.line_chart(df[["total_population"]], height=170)
    st.caption("Range expansion")
    st.line_chart(df[["occupied_area_km2", "front_distance_km"]], height=170)
    st.caption("Front speed (km per step)")
    st.line_chart(df[["front_speed_km_per_step"]], height=140)

    with st.expander("Data & export"):
        st.dataframe(df, use_container_width=True, height=220)
        st.download_button("Download metrics (CSV)", df.to_csv().encode(),
                           file_name="invasion_metrics.csv", mime="text/csv")
        st.download_button("Download final population grid (.npy)",
                           _npy_bytes(sim.N), file_name="population_final.npy")


def _npy_bytes(arr: np.ndarray) -> bytes:
    buf = io.BytesIO()
    np.save(buf, arr)
    return buf.getvalue()


def environment_panel(sim: Simulator) -> None:
    env = sim.env
    land = env.land_mask
    c1, c2 = st.columns(2)
    with c1:
        st.caption("Mean annual temperature (°C)")
        st.image(array_to_png_uri(np.where(land, env.temperature, np.nan),
                                  "coolwarm", mask=land, opaque=True),
                 use_container_width=True)
    with c2:
        st.caption("Annual precipitation (mm)")
        st.image(array_to_png_uri(np.where(land, env.precipitation, np.nan),
                                  "YlGnBu", mask=land, opaque=True),
                 use_container_width=True)

    suit = sim.suitability
    habitable = suit > 0
    st.caption(
        f"Habitat suitability — {habitable.sum():,} of {int(land.sum()):,} land "
        f"cells habitable ({habitable.sum() / max(1, land.sum()):.1%}), "
        f"mean S = {suit[habitable].mean() if habitable.any() else 0:.2f}"
    )
    st.image(array_to_png_uri(suit, "YlGn", 0.0, 1.0, opaque=True, mask=land),
             use_container_width=True)

    temps = env.temperature[land]
    axis = np.linspace(float(temps.min()), float(temps.max()), 200)
    response = np.exp(-0.5 * ((axis - sim.species.niche.t_opt) / max(sim.species.niche.t_tol, 1e-6)) ** 2)
    st.caption("Thermal tolerance curve vs. available temperatures")
    st.line_chart(pd.DataFrame({"Suitability": response}, index=np.round(axis, 1)),
                  height=180)


def occurrence_panel(sim: Simulator) -> None:
    st.write(
        "Pull georeferenced observations from GBIF for the current map extent. "
        "Points are drawn on both maps, and the niche can be fitted directly "
        "from the climate at those locations."
    )
    name = st.text_input("Scientific name", value="Bombus impatiens",
                         placeholder="e.g. Lymantria dispar")
    c1, c2 = st.columns(2)
    if c1.button("Fetch occurrences", use_container_width=True):
        g = sim.env.grid
        with st.spinner("Querying GBIF…"):
            pts = gbif_occurrences(name, g.west, g.south, g.east, g.north, limit=1500)
        st.session_state["gbif_points"] = pts
        if pts:
            st.success(f"{len(pts):,} occurrence records inside the map extent.")
        else:
            st.warning("No records returned (or `pygbif` is not installed).")
    if c2.button("Fit niche from occurrences", use_container_width=True,
                 disabled=not st.session_state.get("gbif_points")):
        fitted = fit_niche_from_occurrences(sim.env, st.session_state["gbif_points"],
                                            base=sim.species.niche)
        if fitted is None:
            st.error("Need at least 10 records on habitable cells to fit a niche.")
        else:
            st.session_state["_preset"] = replace(sim.species, niche=fitted)
            st.session_state["_param_rev"] = st.session_state.get("_param_rev", 0) + 1
            st.success(
                f"Fitted Tₒₚₜ = {fitted.t_opt:.1f} °C (σ = {fitted.t_tol:.1f}), "
                f"Pₒₚₜ = {fitted.p_opt:.0f} mm (σ = {fitted.p_tol:.0f}). "
                "Sliders have been reset to these values."
            )
            st.rerun()
    if st.session_state.get("gbif_points"):
        st.caption(f"{len(st.session_state['gbif_points']):,} points loaded.")
        if st.button("Clear points"):
            st.session_state["gbif_points"] = ()
            st.rerun()


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    st.session_state.setdefault("playing", False)
    st.session_state.setdefault("gbif_points", ())

    env, species, ui = sidebar_controls()
    sim = get_simulator(env, species)
    seeded = sim.seed_rc is not None

    st.title("Species Introduction & Dispersal Simulator")
    st.caption(
        "Gaussian niche envelope → suitability-scaled logistic growth → "
        "kernel dispersal. Click the map to release a founding population, "
        "then watch the invasion wavefront."
    )

    left, right = st.columns([3, 2], gap="large")

    # ---- Left: maps + transport ----------------------------------------- #
    with left:
        default_view = "Simulation view" if seeded else "Seed on map"
        view = st.radio("View", ["Seed on map", "Simulation view"],
                        index=["Seed on map", "Simulation view"].index(
                            st.session_state.get("_view", default_view)),
                        horizontal=True, label_visibility="collapsed")
        st.session_state["_view"] = view

        if view == "Seed on map":
            seeding_map(sim, ui)
        else:
            lc1, lc2 = st.columns([2, 1])
            layer_choice = lc1.selectbox(
                "Overlay", ["Population density", "Relative saturation N/(K·S)",
                            "Occupancy (presence)"], label_visibility="collapsed")
            show_suit = lc2.checkbox("Suitability underlay", value=True)
            simulation_map(sim, layer_choice, show_suit)

        # ---- Transport controls ----------------------------------------- #
        b1, b2, b3, b4, b5 = st.columns(5)
        if b1.button("▶︎ Play", use_container_width=True, disabled=not seeded):
            st.session_state["playing"] = True
            st.session_state["_view"] = "Simulation view"
            st.rerun()
        if b2.button("⏸ Pause", use_container_width=True):
            st.session_state["playing"] = False
        if b3.button("⏭ Step", use_container_width=True, disabled=not seeded):
            st.session_state["playing"] = False
            sim.step()
        if b4.button("⏩ Run all", use_container_width=True, disabled=not seeded):
            st.session_state["playing"] = False
            with st.spinner(f"Running {ui['max_steps'] - sim.t} steps…"):
                sim.run(max(0, ui["max_steps"] - sim.t))
        if b5.button("⟲ Reset", use_container_width=True):
            st.session_state["playing"] = False
            sim.reset(keep_seed=True)
            st.rerun()

        st.caption(
            f"**t = {sim.t} / {ui['max_steps']}** · {sim.summary()}"
            if seeded else "Click the map to release a founding population."
        )
        st.progress(min(1.0, sim.t / max(1, ui["max_steps"])))

    # ---- Right: readouts ------------------------------------------------ #
    with right:
        tabs = st.tabs(["📊 Dynamics", "🌍 Environment", "📍 Occurrences", "ℹ️ Model"])
        with tabs[0]:
            metrics_panel(sim, ui)
        with tabs[1]:
            environment_panel(sim)
        with tabs[2]:
            occurrence_panel(sim)
        with tabs[3]:
            st.markdown(MODEL_NOTES)

    # ---- Animation loop -------------------------------------------------- #
    if st.session_state["playing"] and seeded:
        if sim.t >= ui["max_steps"]:
            st.session_state["playing"] = False
        elif sim.metrics and sim.metrics[-1].total_population <= 0:
            st.session_state["playing"] = False
            st.toast("Population went extinct.", icon="💀")
        else:
            sim.step()
            time.sleep(max(0.0, 1.0 / float(ui["fps"])))
            st.rerun()


MODEL_NOTES = r"""
#### 1 · Habitat suitability

$$S(x,y)=\exp\!\Big(-\tfrac{(T-T_{opt})^2}{2\sigma_T^2}\Big)\cdot
\exp\!\Big(-\tfrac{(P-P_{opt})^2}{2\sigma_P^2}\Big)$$

Multiplicative (Liebig-style): a cell must satisfy *every* axis. Values below
the floor are snapped to 0 so the range edge is crisp.

#### 2 · Local dynamics

$$N_{t+1}=N_t+rN_t\Big(1-\frac{N_t}{K\,S}\Big)-mN_t$$

Carrying capacity is $K\cdot S$, so marginal habitat supports a real but small
population. Cells with $S=0$ are extirpated rather than divided by zero.
An optional Allee threshold extirpates cells below a minimum density.

#### 3 · Dispersal

A fraction $f$ of each cell's population is convolved with a normalised kernel
built in **kilometres** and sampled on the lat/lon lattice (so it stays
circular on the ground, not in index space):

| Kernel | Form | Behaviour |
|---|---|---|
| Gaussian | $e^{-d^2/2\sigma^2}$ | classic diffusive travelling wave, constant speed |
| Exponential | $e^{-d/\sigma}$ | leptokurtic, faster front |
| Fat tail | $(1+d/\sigma)^{-\alpha}$ | satellite colonies, *accelerating* spread |

With **reflecting** boundaries each source cell renormalises its kernel over
reachable habitable cells, so population is conserved exactly at coastlines.
With **absorbing** boundaries propagules that land at sea are lost.

Optional stratified diffusion adds rare human-mediated jumps, which is what
turns a smooth wave into the patchy pattern seen in real invasions.

#### Caveats

Single unstructured population per cell, no age/stage structure, no biotic
interactions, no evolution, static climate. Front speed is sensitive to grid
resolution for fat-tailed kernels — check convergence before quoting numbers.
"""


if __name__ == "__main__":
    main()
