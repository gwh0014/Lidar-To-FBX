# coordinate_transformer.py

from pyproj import CRS, Transformer
import numpy as np

def align_coordinates(points, source_crs, target_crs):
    """
    Transforms a NumPy array of points from a source CRS to a target CRS.
    """
    if source_crs == target_crs:
        print("Source and target CRS are the same. No transformation needed.")
        return points

    print(f"Transforming points from {source_crs.to_string()} to {target_crs.to_string()}...")

    # Create a transformer for the conversion
    # always_xy=True helps avoid axis order confusion
    transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)

    # Perform the transformation
    # The transformer.transform method is highly optimized for NumPy arrays
    transformed_x, transformed_y, transformed_z = transformer.transform(
        points[:, 0], points[:, 1], points[:, 2]
    )

    # Reassemble the transformed points into an (N, 3) array
    aligned_points = np.vstack((transformed_x, transformed_y, transformed_z)).transpose()

    print("Transformation complete.")
    return aligned_points