# point_cloud_processor.py

import laspy
import pdal
import numpy as np

def process_point_cloud(laz_path):
    """
    Reads a LAZ file, extracts its CRS, and uses a PDAL pipeline
    to filter, downsample, and return the points as a NumPy array.
    """
    # Step 1: Use laspy to read the header and extract CRS
    with laspy.open(laz_path) as f:
        laz_header = f.header
        # The CRS is stored in a VLR. We find it and convert to a pyproj.CRS object.
        laz_crs = laz_header.parse_crs()
        print(f"LiDAR CRS found: {laz_crs.to_string()}")

    # Step 2: Define a PDAL pipeline for processing
    # This pipeline reads the LAZ file, filters out noise (classification 7),
    # keeps only ground (2), buildings (6), and high vegetation (5),
    # and then decimates the point cloud to a manageable size.
    pdal_json = {
        "pipeline": [
            {
                "type": "readers.las",
                "filename": laz_path
            },
            {
                "type": "filters.range",
                "limits": "Classification[2:2], Classification[5:6]"
            },
            {
                "type": "filters.decimation",
                "step": 4  # Keep one point for every 4
            },
            {
                "type": "filters.sort",
                "dimension": "Z"
            }
        ]
    }

    # Step 3: Execute the PDAL pipeline
    pipeline = pdal.Pipeline(str(pdal_json).replace("'", '"'))
    #pipeline.validate()
    count = pipeline.execute()
    print(f"PDAL pipeline processed {count} points.")

    # The result is a list of NumPy structured arrays. We'll use the first one.
    arrays = pipeline.arrays
    if not arrays:
        raise ValueError("PDAL pipeline did not produce any points.")

    point_cloud_array = arrays[0]

    # Extract X, Y, Z coordinates into a simple (N, 3) NumPy array
    points = np.vstack((point_cloud_array['X'], point_cloud_array['Y'], point_cloud_array['Z'])).transpose()

    return points, laz_crs