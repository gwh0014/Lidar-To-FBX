import rasterio
from PIL import Image
import numpy as np

def process_geotiff(tif_path, output_texture_path):
    with rasterio.open(tif_path) as dataset:
        # … extract CRS and bounds as before …

        # 1) Read only the first three bands if available,
        #    or replicate a single band into RGB
        if dataset.count >= 3:
            bands = [1, 2, 3]
            image_data = dataset.read(bands)                # shape (3, H, W)
        elif dataset.count == 1:
            band1 = dataset.read(1)                         # shape (H, W)
            # stack into three identical channels
            image_data = np.stack([band1, band1, band1], 0) # shape (3, H, W)
        else:
            # fallback: read whatever is there
            image_data = dataset.read()

        # 2) Move band axis last → (H, W, 3)
        image_data_rgb = np.moveaxis(image_data, 0, -1)

        # 3) Ensure 8-bit unsigned
        if image_data_rgb.dtype != np.uint8:
            maxval = image_data_rgb.max() or 1
            image_data_rgb = (255 * (image_data_rgb / maxval)).astype(np.uint8)

        # 4) Now PIL can handle it as a true RGB image
        img = Image.fromarray(image_data_rgb)
        img.save(output_texture_path)
        print(f"Texture saved to {output_texture_path}")

        return dataset.crs, dataset.bounds
