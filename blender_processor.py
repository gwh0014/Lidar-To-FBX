# blender_processor.py

import sys
import bpy

# confirm the script loaded
print("blender_processor.py loaded — argv:", sys.argv)
sys.stdout.flush()

# scene = bpy.context.scene
# for ob in list (scene.objects):
#     scene.collection.objects.unlink(ob)
#     bpy.data.objects.remove(ob)
# print("Scene should now be empty")

import bmesh
from mathutils import Vector
import os
import argparse


# -------------------------------------------------------------------
# Manual OBJ loader (no add-on required)
def load_obj_manually(obj_path, texture_path):
    import bpy

    verts = []
    faces = []
    with open(obj_path, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if not parts:
                continue
            if parts[0] == 'v':
                # vertex
                verts.append(tuple(map(float, parts[1:])))
            elif parts[0] == 'f':
                # face (just vertex indices, ignore vt/vn)
                idxs = [int(tok.split('/')[0]) - 1 for tok in parts[1:]]
                faces.append(idxs)

    # create mesh + object
    mesh = bpy.data.meshes.new("ImportedMesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("ImportedMesh", mesh)
    bpy.context.collection.objects.link(obj)

    # assign a simple material so bake_texture has something to work with
    img = bpy.data.images.load(texture_path)
    mat = bpy.data.materials.new("TextureMat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    tex_node = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex_node.image = img
    mat.node_tree.links.new(bsdf.inputs["Base Color"], tex_node.outputs["Color"])
    obj.data.materials.append(mat)

    return obj, img

# -------------------------------------------------------------------




# def setup_scene(obj_path, texture_path):
#     print("Blender Commands Started")
#     """Clears the scene and imports the mesh and texture."""
#     # Clear existing objects
#     bpy.ops.object.select_all(action='SELECT')
#     bpy.ops.object.delete()

#     # Import the OBJ mesh
#     bpy.ops.import_scene.obj(filepath=obj_path)

#     # Get the imported object (assuming it's the only one)
#     obj = bpy.context.selected_objects
#     bpy.context.view_layer.objects.active = obj

#     # Load the texture image
#     img = bpy.data.images.load(texture_path)

#     return obj, img




def planar_projection(obj, bounds):
    """
    Creates a new UV layer on obj.data and assigns UVs by
    linearly mapping the world-XY position of each vertex
    into the [0..1] range given the raster bounds.
    """
    min_x, min_y, max_x, max_y = bounds
    span_x = max_x - min_x
    span_y = max_y - min_y

    mesh = obj.data
    # Ensure a UV map exists
    if not mesh.uv_layers:
        mesh.uv_layers.new(name="UVMap")
    uv_layer = mesh.uv_layers.active.data

    # Build a bmesh so we can access loops easily
    bm = bmesh.new()
    bm.from_mesh(mesh)

    obj_matrix = obj.matrix_world
    for face in bm.faces:
        for loop in face.loops:
            world_co = obj_matrix @ loop.vert.co
            u = (world_co.x - min_x) / span_x
            v = (world_co.y - min_y) / span_y
            uv_layer[loop.index].uv = Vector((u, 1.0 - v))

    bm.to_mesh(mesh)
    bm.free()

    print(" Planar UV projection complete.")
    sys.stdout.flush()


def bake_texture(obj, img, width, height, baked_texture_path):

    # Making sure only the terrian is selected ***********************************************************************************************************************************************************
    # bpy.ops.object.select_all(action='DESELECT')
    # obj.select_set(True)
    # bpy.context.view_layer.objects.active = obj

    for o in bpy.context.view_layer.objects:
        o.select_set(False)

    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    print(f"Selected '{obj.name}' for baking/export")
    sys.stdout.flush()

    # if bpy.context.object.mode != 'OBJECT':
    #     bpy.ops.object.mode_set(mode='OBJECT')
    # Make sure cycles is being used since it is the only engine that supports baking
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'

    #OPTIONAL: uncomment the following two lines to force the use of the cpu instead of the GPU
    # if hasattr(scene, 'cycles'):
    #     scene.cycles.device = 'CPU'


    mat = obj.data.materials[0]
    nt  = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    if bsdf is None:
        raise RuntimeError("Could not find Principled BSDF node in material")

    # Create a new image node to bake into
    bake_node = nt.nodes.new("ShaderNodeTexImage")
    bake_node.image = bpy.data.images.new("BakedTexture", width=width, height=height)

    # Link its Color output into the BSDF’s Base Color input
    nt.links.new(
        bake_node.outputs["Color"],
        bsdf.inputs["Base Color"]
    )

    nt.nodes.active = bake_node
    bpy.context.view_layer.objects.active = obj
    
    # Now do the bake
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'},
                        use_clear=True, margin=4)

    # Save out the baked result
    bake_node.image.filepath_raw = baked_texture_path
    bake_node.image.file_format   = 'PNG'
    bake_node.image.save()

    print(f" Baked texture saved to {baked_texture_path}")
    sys.stdout.flush()



# def bake_texture(obj, projected_img, bake_width, bake_height, output_baked_texture_path):
#     """Bakes the projected texture to a new image file."""
#     # Create a new material for the object
#     mat = bpy.data.materials.new(name="BakedMaterial")
#     obj.data.materials.append(mat)
#     mat.use_nodes = True
#     nodes = mat.node_tree.nodes
#     links = mat.node_tree.links
#     bsdf = nodes.get("Principled BSDF")

#     # Create an image texture node for the original projected texture
#     projected_tex_node = nodes.new('ShaderNodeTexImage')
#     projected_tex_node.image = projected_img
#     links.new(projected_tex_node.outputs['Color'], bsdf.inputs)

#     # Create a new image to bake to
#     baked_image = bpy.data.images.new(
#         name="BakedTexture",
#         width=bake_width,
#         height=bake_height
#     )

#     # Create an image texture node for the bake target and make it active
#     bake_node = nodes.new('ShaderNodeTexImage')
#     bake_node.image = baked_image
#     nodes.active = bake_node

#     # Configure and execute the bake
#     print("Baking texture...")
#     bpy.context.scene.render.engine = 'CYCLES' # Baking works best with Cycles
#     bpy.context.scene.cycles.device = 'GPU' # Use GPU if available
#     bpy.context.scene.render.bake.use_pass_direct = False
#     bpy.context.scene.render.bake.use_pass_indirect = False
#     bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'})

#     # Save the baked image
#     baked_image.filepath_raw = output_baked_texture_path
#     baked_image.file_format = 'PNG'
#     baked_image.save()
#     print(f"Baked texture saved to {output_baked_texture_path}")

#     # Clean up the material: remove the projected texture node
#     # and link the new baked texture to the shader.
#     links.clear()
#     nodes.remove(projected_tex_node)
#     links.new(bake_node.outputs['Color'], bsdf.inputs)



def export_to_fbx(output_fbx_path):
    """Exports the current selection to an Unreal-ready FBX file."""
    print(f"Exporting to FBX: {output_fbx_path}")
    bpy.ops.export_scene.fbx(
        filepath=output_fbx_path,
        check_existing=True,
        use_selection=True,
        use_active_collection=False,
        global_scale=1.0,
        apply_unit_scale=True,
        # Unreal Engine's coordinate system is -Y Forward, Z Up
        axis_forward='-Y',
        axis_up='Z',
        object_types={'MESH'},
        use_mesh_modifiers=True,
        path_mode='COPY',
        embed_textures=True
    )
    print("FBX export complete.")

def parse_args():
    # grab only the flags after the “--” separator
    if "--" in sys.argv:
        idx = sys.argv.index("--") + 1
        cli = sys.argv[idx:]
    else:
        cli = sys.argv[1:]

    p = argparse.ArgumentParser(description="Texture + export FBX in Blender")
    p.add_argument("--obj",           required=True, help="Path to the intermediate OBJ")
    p.add_argument("--texture",       required=True, help="Path to the source texture PNG")
    p.add_argument("--baked-texture", required=True, help="Where to save the baked PNG")
    p.add_argument("--fbx",           required=True, help="Where to write the FBX")
    p.add_argument("--bounds",        required=True, nargs=4, type=float,
                   metavar=("LEFT","BOTTOM","RIGHT","TOP"),
                   help="GeoTIFF bounds for UV projection")
    return p.parse_args(cli)

if __name__ == "__main__":
    args = parse_args()

    # 1) Import mesh + texture
    #obj, img = setup_scene(args.obj, args.texture)
    print("1) Importing mesh via manual loader")
    obj, img = load_obj_manually(args.obj, args.texture)

    # 2) Planar UV projection
    print("2) Projecting UVs")
    planar_projection(obj, args.bounds)

    # 3) Bake into a new image, using the same resolution as the source:
    max_res = 4096
    w, h = img.size  # Blender image: .size → (width, height)
    width = min(w, max_res)
    height = min(h, max_res)
    print(f"3) Baking to {args.baked_texture} at {width}×{height}")
    bake_texture(obj, img, width, height, args.baked_texture)

    #selecting only terrain for export
    # bpy.ops.object.select_all(action='DESELECT')
    # obj.select_set(True)
    # bpy.context.view_layer.objects.active = obj

    for o in bpy.context.view_layer.objects:
        o.select_set(False)

    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    print(f"Selected '{obj.name}' for baking/export")
    sys.stdout.flush()

    # 4) Export to FBX
    print(f"4) Exporting to FBX: {args.fbx}")
    export_to_fbx(args.fbx)