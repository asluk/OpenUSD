# Third-party datasets

## deutschebahn-rails.usda

- **Source:** NVIDIA-Omniverse / OpenUSD-plugin-samples
  (`resources/wgs84/deutschebahn-rails.usda`)
  <https://github.com/NVIDIA-Omniverse/OpenUSD-plugin-samples>
- **License:** Apache License 2.0 (same as the source repository).
- **What it is:** a real geospatial dataset — Deutsche Bahn railway track curves
  near Hamburg, Germany (~53.49° N, 10.21° E) — authored in the **original
  Omniverse geospatial schema** (`OmniWGS84ReferencePositionAPI` on a root
  reference anchor + `OmniWGS84LocalPositionAPI` on each curve group, with
  `omni:geospatial:wgs84:*` attributes; note the source uses **lat-first**
  ordering). The demo layers the rail curves **on top of geospatial tile ground
  planes** (`MapGeo0/1/4`, textured with the `quadnode-*.png` quadtree imagery
  vendored alongside) — both layers are georeferenced, so it exercises true
  rails-on-tiles co-registration, not just isolated points.
- **Why it is here:** to run a genuinely third-party dataset, authored in a
  *different* schema, through this bundle's reference runtime — evidence the
  runtime is not overfit to our own Earth-2 authoring. It is converted to the
  Esri-aligned `crs:binding` / `crs:position` form by
  `src/convert_omni_geospatial.py` (which swaps lat/lon into our
  `(lon/E, lat/N, h)` contract), then resolved and checked against closed-form
  geodesy in `src/generalization_suite.py`.
- **Modifications:** none to these vendored files; conversion is performed at
  runtime into `out/railway_georef.usda`. The `quadnode-*.png` tiles are the
  geospatial ground imagery the rails render on top of.
