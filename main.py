# main.py

import argparse
import subprocess
import os
from pathlib import Path
import open3d as o3d

# Import our custom processing modules
from point_cloud_processor import process_point_cloud
from texture_processor import process_geotiff
from coordinate_transformer import align_coordinates
from mesh_generator import generate_mesh_from_points, save_intermediate_mesh

def main():
    parser = argparse.ArgumentParser(
        description="Automated pipeline to convert LAZ and TIF to a textured FBX."
    )
    parser.add_argument("laz_input", type=str, help="Path to the input.laz file.")
    parser.add_argument("tif_input", type=str, help="Path to the input.tif file.")
    parser.add_argument("fbx_output", type=str, help="Path for the output.fbx file.")
    parser.add_argument("--blender-path", type=str, default="blender", help="Path to the Blender executable.")
    args = parser.parse_args()

    # Create a temporary directory for intermediate files
    temp_dir = Path("./temp_geo_processing")
    temp_dir.mkdir(exist_ok=True)
    
    intermediate_obj = (temp_dir / "mesh.obj").resolve()
    intermediate_png = (temp_dir / "texture.png").resolve()
    baked_texture_png = (temp_dir / "baked_texture.png").resolve()
    blender_script_path = (Path(__file__).parent / "./blender_processor.py").resolve()
    output_fbx = Path(args.fbx_output).resolve() 

    try:
        # --- STAGE 1: DATA INGESTION AND ALIGNMENT ---
        print("--- STAGE 1: PROCESSING GEOSPATIAL DATA ---")
        points, laz_crs = process_point_cloud(args.laz_input)
        tif_input_path = Path(args.tif_input).resolve()
        tif_crs, tif_bounds = process_geotiff(str(tif_input_path), str(intermediate_png))
        aligned_points = align_coordinates(points, laz_crs, tif_crs)

        # --- STAGE 2: MESH GENERATION ---
        print("\n--- STAGE 2: GENERATING 3D MESH ---")
        mesh = generate_mesh_from_points(aligned_points)
        save_intermediate_mesh(mesh, str(intermediate_obj))

        # Small check to see that stage two actually produced a mesh
        mesh = o3d.io.read_triangle_mesh(str(intermediate_obj))
        print(f"DEBUG: mesh.obj → {len(mesh.vertices)} verts, {len(mesh.triangles)} tris")

        # --- STAGE 3: BLENDER PROCESSING ---
        print("\n--- STAGE 3: RUNNING BLENDER FOR TEXTURING AND EXPORT ---")
        blender_command = [
            args.blender_path,
            "--background",
            "--enable-autoexec",
            "--python", str(blender_script_path),
            "--", # Argument separator
            "--obj", str(intermediate_obj),
            "--texture", str(intermediate_png),
            "--baked-texture", str(baked_texture_png),
            #"--fbx", args.fbx_output,
            "--fbx", str(output_fbx),
            #"--bounds", *[str(b) for b in tif_bounds]
            "--bounds", *map(str, tif_bounds),
        ]

        # The blender_processor.py script needs to be modified to accept these arguments
        # using Python's argparse or by parsing sys.argv
        
        print("Running Blender commands:", blender_command) # delete this later 

        #subprocess.run(blender_command, check=True)

        result = subprocess.run(
            blender_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        print("→ Blender exit code:", result.returncode)
        print("→ Blender stdout:\n", result.stdout)
        print("→ Blender stderr:\n", result.stderr)
        if result.returncode != 0:
            raise RuntimeError(f"Blender failed (exit {result.returncode})")


        print("\n--- PIPELINE COMPLETED SUCCESSFULLY ---")
        print(f"Final output saved to: {args.fbx_output}")

    except Exception as e:
        print(f"\n--- PIPELINE FAILED ---")
        print(f"An error occurred: {e}")
    finally:
        # Optional: Clean up temporary files
        # import shutil
        # shutil.rmtree(temp_dir)
        pass

if __name__ == "__main__":
    # The blender_processor.py script also needs its own __main__ block
    # to parse arguments passed after the '--' separator.
    # This is left as an implementation detail for the final script.
    main()