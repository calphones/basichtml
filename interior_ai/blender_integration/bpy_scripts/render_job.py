"""
Blender Python render job — executed inside blender --background.
Usage: blender --background --python render_job.py -- <scene_json> <output_path>
"""
import bpy
import json
import sys
import math
import os

argv = sys.argv
separator = argv.index("--") + 1 if "--" in argv else len(argv)
args = argv[separator:]

if len(args) < 2:
    print("ERROR: Usage: render_job.py -- <scene.json> <output.png>")
    sys.exit(1)

scene_path, output_path = args[0], args[1]
with open(scene_path) as f:
    data = json.load(f)

# ── Reset scene ────────────────────────────────────────────────────────────
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete()
for mat in list(bpy.data.materials):
    bpy.data.materials.remove(mat)

scene = bpy.context.scene
render = scene.render
render.resolution_x, render.resolution_y = data["resolution"]
render.filepath = output_path
render.image_settings.file_format = "PNG"

mode = data.get("render_mode", "preview")
if mode == "photoreal":
    scene.render.engine = "CYCLES"
    scene.cycles.samples = data.get("samples", 512)
    scene.cycles.use_denoising = True
    try:
        scene.cycles.device = "GPU"
    except Exception:
        scene.cycles.device = "CPU"
else:
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = data.get("samples", 64)

# ── Materials ──────────────────────────────────────────────────────────────
def make_material(name, mat_data):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    output = nodes.new("ShaderNodeOutputMaterial")
    mat.node_tree.links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    c = mat_data.get("base_color", [0.8, 0.75, 0.7])
    bsdf.inputs["Base Color"].default_value = (c[0], c[1], c[2], 1.0)
    bsdf.inputs["Roughness"].default_value = mat_data.get("roughness", 0.5)
    bsdf.inputs["Metallic"].default_value = mat_data.get("metallic", 0.0)
    tex_path = mat_data.get("texture_path")
    if tex_path and os.path.exists(tex_path):
        tex_node = nodes.new("ShaderNodeTexImage")
        tex_node.image = bpy.data.images.load(tex_path)
        mat.node_tree.links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])
    return mat

materials = {}
for name, mat_data in data.get("materials", {}).items():
    materials[name] = make_material(name, mat_data)

def get_mat(name):
    return materials.get(name) or make_material(name, {"base_color": [0.8, 0.75, 0.7]})

# ── Walls ──────────────────────────────────────────────────────────────────
for wall in data.get("walls", []):
    sx, sy = wall["start"]
    ex, ey = wall["end"]
    dx, dy = ex - sx, ey - sy
    length = math.hypot(dx, dy)
    if length < 0.01:
        continue
    angle = math.atan2(dy, dx)
    h = wall.get("height", 2.74)
    t = wall.get("thickness", 0.2)
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = bpy.context.active_object
    obj.name = wall.get("id", "wall")
    obj.scale = (length, t, h)
    obj.location = ((sx + ex) / 2, (sy + ey) / 2, h / 2)
    obj.rotation_euler[2] = angle
    obj.data.materials.append(get_mat("wall_paint"))

# ── Floors ──────────────────────────────────────────────────────────────────
for room in data.get("floors", []):
    poly = room.get("polygon", [])
    if len(poly) < 3:
        continue
    verts = [(p[0], p[1], 0) for p in poly]
    mesh = bpy.data.meshes.new("floor_mesh")
    obj = bpy.data.objects.new(f"floor_{room['id']}", mesh)
    bpy.context.collection.objects.link(obj)
    mesh.from_pydata(verts, [], [list(range(len(verts)))])
    mesh.update()
    obj.data.materials.append(get_mat("floor"))

# ── Furniture ──────────────────────────────────────────────────────────────
for item in data.get("furniture", []):
    cat = item.get("category", "seating")
    pos = item.get("position", [0, 0, 0])
    scale = item.get("scale", [1, 1, 1])
    rot_z = math.radians(item.get("rotation_z", 0))
    model_path = item.get("model_path")
    if model_path and os.path.exists(model_path):
        ext = os.path.splitext(model_path)[1].lower()
        if ext == ".glb":
            bpy.ops.import_scene.gltf(filepath=model_path)
        elif ext == ".fbx":
            bpy.ops.import_scene.fbx(filepath=model_path)
        imported = bpy.context.selected_objects
        if imported:
            for ob in imported:
                ob.location = (pos[0], pos[1], pos[2])
                ob.rotation_euler[2] = rot_z
    else:
        bpy.ops.mesh.primitive_cube_add(size=1)
        obj = bpy.context.active_object
        obj.name = item.get("name", cat)
        obj.scale = (scale[0], scale[1], scale[2])
        obj.location = (pos[0] + scale[0]/2, pos[1] + scale[1]/2, pos[2] + scale[2]/2)
        obj.rotation_euler[2] = rot_z
        mat_name = "sofa_fabric" if "sofa" in cat or "chair" in cat else "wood_surface"
        obj.data.materials.append(get_mat(mat_name))

# ── Lights ─────────────────────────────────────────────────────────────────
for lt in data.get("lights", []):
    pos = lt.get("position", [0, 0, 2.5])
    color = lt.get("color", [1.0, 0.95, 0.8])
    intensity = lt.get("intensity", 3.0)
    ltype = lt.get("type", "recessed")
    bpy.ops.object.light_add(
        type="AREA" if ltype in ("natural", "recessed") else "POINT",
        location=(pos[0], pos[1], pos[2]),
    )
    light = bpy.context.active_object.data
    light.energy = intensity * 100
    light.color = (color[0], color[1], color[2])
    if hasattr(light, "size"):
        light.size = 0.5

# ── HDRI world ─────────────────────────────────────────────────────────────
hdri_path = data.get("hdri_path")
if hdri_path and os.path.exists(hdri_path):
    world = bpy.context.scene.world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    nodes.clear()
    background = nodes.new("ShaderNodeBackground")
    env_tex = nodes.new("ShaderNodeTexEnvironment")
    env_tex.image = bpy.data.images.load(hdri_path)
    output_w = nodes.new("ShaderNodeOutputWorld")
    world.node_tree.links.new(env_tex.outputs["Color"], background.inputs["Color"])
    world.node_tree.links.new(background.outputs["Background"], output_w.inputs["Surface"])
    background.inputs["Strength"].default_value = 0.8

# ── Camera ─────────────────────────────────────────────────────────────────
cam_data = data.get("camera")
if cam_data:
    bpy.ops.object.camera_add(location=cam_data["position"])
    cam_obj = bpy.context.active_object
    scene.camera = cam_obj
    target = cam_data.get("target", [0, 0, 1])
    dx = target[0] - cam_data["position"][0]
    dy = target[1] - cam_data["position"][1]
    dz = target[2] - cam_data["position"][2]
    cam_obj.rotation_euler[0] = math.atan2(math.hypot(dx, dy), -dz)
    cam_obj.rotation_euler[2] = math.atan2(dy, dx) + math.pi / 2
    cam_obj.data.lens_unit = "FOV"
    cam_obj.data.angle = math.radians(cam_data.get("fov", 60))
else:
    bpy.ops.object.camera_add(location=(0, -6, 1.6))
    cam_obj = bpy.context.active_object
    cam_obj.rotation_euler = (math.radians(80), 0, 0)
    scene.camera = cam_obj

# ── Render ─────────────────────────────────────────────────────────────────
bpy.ops.render.render(write_still=True)
print(f"Render complete: {output_path}")
