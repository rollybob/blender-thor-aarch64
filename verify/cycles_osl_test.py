# OSL verification for the Thor aarch64 Blender build.
# Proves the CPU-only OSL we just built actually compiles + executes a shader:
#  - enables Cycles OSL shading system
#  - builds a material whose surface comes from an OSL Script node (internal .osl)
#  - the shader emits a distinctive color; a matching render mean proves OSL ran
#    (a broken OSL would fail to compile the node and abort the render).
# OSL on a non-OptiX build runs on CPU only (Jetson has no OptiX), so we render on CPU.
import bpy, time, sys

scene = bpy.context.scene
scene.render.engine = 'CYCLES'

# Enable the OSL shading system (robust to Bool-vs-Enum across versions).
prop = scene.cycles.bl_rna.properties['shading_system']
if prop.type == 'BOOLEAN':
    scene.cycles.shading_system = True
else:
    scene.cycles.shading_system = 'OSL'
print('SHADING_SYSTEM:', scene.cycles.shading_system)

# OSL => CPU device on a non-OptiX build.
scene.cycles.device = 'CPU'
scene.cycles.samples = 16
scene.render.resolution_x = 128
scene.render.resolution_y = 128
scene.cycles.use_denoising = False

# Clean scene, add a cube to shade + camera + light.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
cube = bpy.context.object
bpy.ops.object.light_add(type='SUN')
bpy.ops.object.camera_add(location=(4, -4, 3), rotation=(1.1, 0, 0.785))
scene.camera = bpy.context.object

# OSL shader source: emit a distinctive red-orange so we can confirm it executed.
OSL_SRC = '''
shader emit_test(
    color Cin = color(0.90, 0.20, 0.05),
    output closure color Cout = 0)
{
    Cout = Cin * emission();
}
'''
txt = bpy.data.texts.new('emit_test.osl')
txt.write(OSL_SRC)

mat = bpy.data.materials.new('osl_mat')
mat.use_nodes = True
nt = mat.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
out_node = nt.nodes.new('ShaderNodeOutputMaterial')
osl_node = nt.nodes.new('ShaderNodeScript')
osl_node.mode = 'INTERNAL'
osl_node.script = txt              # triggers oslc compile of the .osl
# The script node's outputs are derived from the shader's output params.
if 'Cout' not in osl_node.outputs:
    print('RESULT: OSL_NODE_NO_OUTPUT (compile failed?)'); sys.exit(3)
nt.links.new(osl_node.outputs['Cout'], out_node.inputs['Surface'])
cube.data.materials.append(mat)

out = '/tmp/cycles_osl_test.png'
scene.render.filepath = out
scene.render.image_settings.file_format = 'PNG'

t0 = time.time()
bpy.ops.render.render(write_still=True)
dt = time.time() - t0
print(f'RENDER_DONE device={scene.cycles.device} time={dt:.2f}s out={out}')

img = bpy.data.images.load(out)
px = img.pixels[:]
n = len(px)
# Average per-channel over RGB (ignore alpha) to check the emitted color.
r = sum(px[0::4]) / (n // 4)
g = sum(px[1::4]) / (n // 4)
b = sum(px[2::4]) / (n // 4)
mx = max(px)
print(f'PIXEL_STATS n={n} max={mx:.4f} R={r:.4f} G={g:.4f} B={b:.4f}')
# Expect red-dominant emission if OSL ran (R clearly > G and B, non-black).
osl_ran = mx > 0.01 and r > g and r > b and r > 0.05
print('RESULT:', 'OSL_OK' if osl_ran else 'OSL_FAIL')
