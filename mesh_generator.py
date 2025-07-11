# mesh_generator.py

import open3d as o3d
import numpy as np

def generate_mesh_from_points(points):
    """
    Generates a 3D mesh from a NumPy array of points using Open3D.
    """
    # Step 1: Create an Open3D PointCloud object
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)

    # Step 2: Estimate normals
    # The algorithm analyzes neighboring points to determine the surface orientation
    print("Estimating normals...")
    pcd.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.5, max_nn=30)
    )

    # Orient the normals consistently
    # This ensures all normals point "outward" from the surface
    pcd.orient_normals_consistent_tangent_plane(100)
    print("Normals estimated and oriented.")

    # In mesh_generator.py, inside generate_mesh_from_points()

    # Option A: Poisson Surface Reconstruction
    print("Performing Poisson surface reconstruction...")
    with o3d.utility.VerbosityContextManager(o3d.utility.VerbosityLevel.Debug) as cm:
       mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
           pcd, depth=9, width=0, scale=1.1, linear_fit=False
       )

    # Post-processing: remove low-density vertices
    print("Filtering low-density vertices...")
    vertices_to_remove = densities < np.quantile(densities, 0.05)
    mesh.remove_vertices_by_mask(vertices_to_remove)

    # # Option B: Ball Pivoting Algorithm
    # print("Performing Ball Pivoting reconstruction...")

    # # Calculate a suitable radius based on point cloud density
    # distances = pcd.compute_nearest_neighbor_distance()
    # avg_dist = np.mean(distances)
    # radii = [avg_dist, avg_dist * 2, avg_dist * 4]

    # mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(
    #   pcd, o3d.utility.DoubleVector(radii)
    # )


    # Step 4: Post-process the mesh
    print("Simplifying mesh...")
    # Decimate the mesh to reduce polygon count for better performance
    # Target 100,000 triangles for this example
    mesh = mesh.simplify_quadric_decimation(target_number_of_triangles=100000)

    # Remove small, disconnected pieces of geometry
    mesh.remove_degenerate_triangles()
    mesh.remove_duplicated_triangles()
    mesh.remove_duplicated_vertices()
    mesh.remove_non_manifold_edges()


    print("Mesh generation and processing complete.")
    return mesh

def save_intermediate_mesh(mesh, output_obj_path):
    """Saves the Open3D mesh to an OBJ file."""
    o3d.io.write_triangle_mesh(output_obj_path, mesh, write_ascii=True)
    print(f"Intermediate mesh saved to {output_obj_path}")