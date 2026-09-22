# Datasets and workflows for the next implementation

Use the earlier work to supply real inputs and useful questions. The current
functional requirements determine runtime behavior. An old schema, converter,
resolved output or error threshold is not an acceptance oracle for this build.

`dataset-catalog.json` records each input, its provenance and the workflows it
exercises. Every run emits `WORKFLOWS.md` with current requirement titles, runnable
evidence, the next demonstration and the decisions it depends on. Missing data,
unverified controls and missing implementations remain visible independently.

## Railway: preserve the original features, then demonstrate placement

The original GeoJSON supplied by Aaron lets us follow the source features into
the provider's USD asset. The checks compare object identities, geometry kinds,
LineString vertex counts and the first coordinate used for each source anchor.
The source GeoJSON uses longitude/latitude order; the Omniverse USD attributes
encode latitude first. That conversion is explicit at the data boundary.

These checks expose lost features and axis-order mistakes before a new resolver
exists. They do not yet validate every interior vertex, polygon topology,
orientation or alignment with the map tiles. The next demonstration needs those
placements, a visible wrong-frame/axis control, and independent reference values.

The GeoJSON declares EPSG:4326 and contains a third ordinate, but supplies no
vertical datum or epoch. Preserve that ordinate. Do not silently relabel it as an
ellipsoidal height in acceptance tests. Geographic-to-ECEF component probes are
explicitly hypothetical interpretations, not proof of absolute survey accuracy.

Fetch the original USD and three map tiles directly from the pinned
[NVIDIA sample data revision](https://github.com/NVIDIA-Omniverse/OpenUSD-plugin-samples/tree/0411df6fd1713b70af3e92f5d0acaf634484ab30/resources/wgs84).
The cache retains upstream LICENSE. Keep Aaron's original GeoJSON local until
redistribution terms are established. No old conversion or runtime script runs.

## Scalar field: data survives a change of visualization

The available local `gfs_t2m.nc` contains a 37 by 72 scalar field. It has no source,
forecast time, CRS or units metadata, so the filename alone does not establish
that it is a NOAA GFS observation. Keep it as a data-handling sample and seek a
provider-documented field for scientific/geodetic acceptance.

The current checks preserve all scalar values and source bytes. A stock USD
composition experiment adds removable glyph geometry to a small set of neutral
sample records, without re-authoring their coordinates or values. A separate
coordinate probe declares WGS 84, degree axes and a constructed zero-height
surface explicitly. Those assumptions do not become the source's CRS or a USD
position-carrier decision. Geospatial scene placement and renderer/analysis
agreement remain future demonstrations.

## Geographic and projected cases

Retain New York, Sydney, Wellington, Quito and Svalbard as diverse geographic
stimuli, and add generated locations so the implementation cannot depend on a
fixed list of landmarks. Recompute expectations from ellipsoid equations.

UTM and national/state-grid variants remain part of the workflow inventory.
The earlier projected cases used PROJ to generate some inputs, and the quoted
NOAA NCAT controls lack archived provider responses and complete datum/epoch
provenance. Neither is promoted to independent ground truth. Obtain complete
provider records before using projected coordinates as acceptance references.

The site/calibration attachment continues through `--aeco-zip`. Its checks
reproduce the partner's stock-USD baseline; they do not adopt its binding/reset
conventions into the new runtime.

## Reproduce the intake

The data cache must live outside the source repository. Fetching is explicit;
ordinary builds never download files or execute data-provider scripts.

```sh
python datasets.py fetch --root /external/geospatial-datasets
python datasets.py import --root /external/geospatial-datasets --dataset railway-geojson --source /local/1kmE4334N3375.geojson
python datasets.py import --root /external/geospatial-datasets --dataset scalar-field --source /local/gfs_t2m.nc
python -m pip install -r requirements-datasets.txt
python run.py --output /external/run-new --dataset-root /external/geospatial-datasets
```

Each import/download must match the catalog's size and SHA-256. A new file needs
a reviewed provenance/catalog update; a familiar filename is insufficient.
No raw dataset is included in the public delivery. Runs record availability,
hashes, checks and workflow gaps; delivery preserves the catalog and sanitized
workflow evidence. Without a cache, geographic and synthetic checks still run
and optional asset checks skip explicitly.

## Delivery should explain what each demonstration establishes

Choose a workflow question, show the relevant input and observed behavior, explain
the mechanism, and connect the evidence to a decision. Use negative controls and
independent reference values where they answer a real doubt. The README develops
that explanation; the PR guides review, and the deck makes the argument visual.
Keep process counts and hash receipts as supporting evidence. Reusing a dataset
does not commit this implementation to the previous architecture or presentation.
