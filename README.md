# Species Introduction & Dispersal Simulator

Drop a species on a map, watch it invade.

A vectorised reaction–diffusion model on a geographic grid: a Gaussian niche
envelope turns climate into habitat suitability, suitability scales a logistic
carrying capacity, and a normalised dispersal kernel moves individuals between
cells each step. Streamlit front end with click-to-seed, live playback, and
range-expansion diagnostics.

```
pip install -r requirements.txt
streamlit run app.py
```

No data download required — the app ships with a procedural climate so it runs
the moment you clone it.

---

## Files

| File | Role |
|---|---|
| `model.py` | Simulation engine: grid geometry, niche, logistic growth, dispersal kernel, metrics. Pure NumPy/SciPy, no UI imports. |
| `data.py` | Environment providers: procedural climate, GeoTIFF loader (`rasterio`), GBIF occurrences + niche fitting. |
| `species.py` | Seven parameter presets, from a slow conifer to a jump-dispersing mollusc. |
| `app.py` | Streamlit UI: Folium click-to-seed map, PyDeck heatmap playback, charts, exports. |
| `demo.py` | Headless runner — same engine, no browser. Good for CI and profiling. |
| `tests/test_model.py` | 34 behavioural tests: mass conservation, logistic equilibria, kernel properties, spread monotonicity. |

---

## The model

**1 · Habitat suitability** — a multiplicative (Liebig) envelope over each
environmental axis:

$$S(x,y)=\exp\left(-\frac{(T-T_{opt})^2}{2\sigma_T^2}\right)\cdot\exp\left(-\frac{(P-P_{opt})^2}{2\sigma_P^2}\right)$$

Values under a small floor snap to zero, so the range edge is a hard boundary
rather than an asymptote. Ocean and nodata cells are masked out.

**2 · Local dynamics** — discrete logistic growth with suitability-scaled
capacity and density-independent mortality:

$$N_{t+1}=N_t+rN_t\left(1-\frac{N_t}{K\,S}\right)-mN_t$$

Analytic equilibrium is $N^* = K S (1 - m/r)$, which the test suite verifies.
Cells with $S=0$ are extirpated rather than divided by zero, growth is clipped
at $-N$ so large $r$ can't go negative, and density is bounded at $2KS$ so
overshoot oscillations stay bounded instead of diverging. An optional Allee
threshold extirpates cells below a minimum density — small founder patches can
then fail to establish, which is the point.

**3 · Dispersal** — a fraction $f$ of each cell's population is convolved with
a normalised kernel:

| Kernel | Form | Behaviour |
|---|---|---|
| Gaussian | $e^{-d^2/2\sigma^2}$ | classic diffusive travelling wave, constant speed |
| Exponential | $e^{-d/\sigma}$ | leptokurtic, faster front |
| Fat tail | $(1+d/\sigma)^{-\alpha}$ | satellite colonies, *accelerating* spread |

Two details that matter:

*   The kernel is built in **kilometres** and then sampled on the lat/lon
    lattice, so it stays circular on the ground. At 48°N a 0.1° cell is ~7.4 km
    tall but ~5.1 km wide — an isotropic-in-index-space kernel would give you a
    front that spreads visibly faster east–west, which is a bug, not ecology.
*   With **reflecting** boundaries each source cell renormalises its kernel over
    the habitable targets within reach, so population is conserved *exactly*
    against a coastline (verified to 1e-6 in the tests). **Absorbing** boundaries
    let propagules that land at sea die, which is the right choice for a genuine
    marine barrier.

Optional stratified diffusion adds rare human-mediated jumps — short natural
kernel plus a low-probability long hop. That is what turns a smooth wave into
the patchy leapfrog pattern real invasions show.

Measured on a 104×236 grid (contiguous USA at 0.25°): **~500–750 steps/second**,
with the fat-tailed kernel producing a front ~2.2× faster than Gaussian and a
positive acceleration trend, as theory predicts.

---

## Using real climate data

Drop GeoTIFFs into `data/` and they appear in the sidebar layer pickers.
[WorldClim v2](https://worldclim.org/data/worldclim21.html) 10-arcmin is the
easy starting point:

* `wc2.1_10m_bio_1.tif` — mean annual temperature (°C), scale factor **1.0**
* `wc2.1_10m_bio_12.tif` — annual precipitation (mm), no scaling

WorldClim **v1** stores °C × 10 — set the scale factor to **0.1**. Rasters are
windowed and bilinearly reprojected onto the chosen region; nodata cells become
ocean, so WorldClim's ocean fill gives you a coastline for free.

## Occurrence data

The Occurrences tab pulls georeferenced GBIF records for the current map extent
(`pygbif`), draws them on both maps, and can fit the niche directly from the
climate at those points. The fit uses the **median** as the optimum and a
quantile-based spread as σ — robust to the sampling bias toward roads and
cities, and to the handful of misidentifications every GBIF query contains.
Both `pygbif` and `rasterio` are optional: without them the app falls back to
the procedural climate and no occurrence overlay, rather than refusing to start.

---

## Extending it

The engine and the UI share no state beyond the `Simulator` object, so:

* **New environmental axis** — add the layer to `Environment`, add a response
  term to `habitat_suitability`. Nothing else changes.
* **New kernel** — one branch in `make_dispersal_kernel`. Normalisation,
  anisotropy, and boundary handling are already handled downstream.
* **Stage structure or multiple species** — replace `logistic_step` with a
  function over a stacked `(n_stages, rows, cols)` array; the dispersal operator
  already broadcasts if you loop the stage axis.
* **Climate change** — mutate `env.temperature` inside the step loop and call
  `sim.update_params(...)`; suitability and the extirpation of newly unsuitable
  cells are recomputed for you.

## Caveats

Single unstructured population per cell. No age or stage structure, no biotic
interactions, no evolution of tolerance, static climate unless you drive it.
Front speed is resolution-sensitive for fat-tailed kernels — check convergence
across grid resolutions before quoting a spread rate. The preset parameters are
order-of-magnitude sensible, not calibrated; refit against real demographic data
before drawing conclusions about a real species.

## Tests

```
pytest -q
```
