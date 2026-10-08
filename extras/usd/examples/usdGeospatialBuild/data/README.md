# Dataset sources and conditional assumptions

The CSV and WKT files under Colorado/ and France/, and the Colorado LandXML,
were supplied by Sébastien Trapp for the geospatial work. The source archive
states Apache License 2.0; see LICENSE-partner.txt. Original file bytes are
retained. Its control coordinates were computed using PROJ 9.8.1; they are
useful intake checks, not an independent geodetic-engine certification.
The two France COORDINATEMETADATA examples are negative tests for deferred
coordinate-epoch support. Their CRS frame epochs are not removed.

The Eiffel model is unmodified. Its embedded CC BY 4.0 credit and source URL
are retained and repeated in manifest.json. The assembly explicitly corrects
its known Y-up geometry to Z-up. The asset's erroneous metersPerUnit=0.01
metadata is retained; this demonstration treats its actual mesh units as metres.
The placed origin and orientation are supplied illustration facts. Ground and
control markers give context; they are not surveyed Paris ground truth.

The Colorado LandXML supplies original breaklines (14,359 vertices across 710
coordinate parts), not a reconstructed surveyed terrain surface. LandXML
northing/easting/height order is converted to the declared easting/northing/height
order. US survey feet are converted to stage metres before local geometry is
written. Its full site-calibration WKT is retained as the coordinate definition.

railway.geojson is Aaron Luk's original supplied railway data. Every one of its
15,822 vertices and all 2,386 coordinate parts are carried into the query data.
Its EPSG:4326 label does not establish the third coordinate's height datum.
WGS84 ellipsoidal height is a conditional interpretation for this demonstration;
no surveyed height accuracy is claimed and no missing heights are silently zeroed.
The original feature topology remains in railway.geojson and rail-topology.npz.

City red and near-infrared bands are newly generated illustrative data, not
measured imagery. Their 64 x 64 coordinate grid, fixed 80 m ellipsoidal height
and observation time are explicit. The result is an NDVI selection workflow,
not a claim about vegetation in Paris.

gfs_t2m.nc is the original supplied 37 x 72 scalar field. Its source file has
no height or physical-unit metadata. Positions use explicitly assumed zero
ellipsoidal height. Time zero preserves the original values; time ten adds a
labeled synthetic perturbation. No observed change, forecast or climate trend
is inferred. Values, grid indices, coordinates and recorded times stay associated.

manifest.json records original source hashes and credits. resources.json records
the two separately downloaded transformation grids and their verified hashes.
They are engine configuration, not additional authored USD geospatial properties.
Network lookup is disabled during evidence collection. Refer to the respective
PROJ-data distribution for resource licensing; grids are not bundled here.
