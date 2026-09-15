# EEVEE headless render smoke test.
# Run: blender --background --python eevee_headless_test.py
# Goal: confirm the realtime rasterizer (EEVEE / EEVEE-Next) can render to a PNG
# with NO monitor/window. Blender historically could NOT do EEVEE in --background
# (no GL context); newer builds may create an EGL offscreen context. This test tells
# us at RUNTIME whether that works on this box, per the "build success != working
# feature" lesson.
import bpy, os, sys

OUT = "/tmp/eevee_headless_out.png"

# Pick the EEVEE engine id available in this Blender (4.5 renamed Next -> BLENDER_EEVEE).
scene = bpy.context.scene
engine_prop = scene.render.bl_rna.properties["engine"]
avail = [it.identifier for it in engine_prop.enum_items]
print("AVAILABLE ENGINES:", avail)
engine = None
for cand in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    if cand in avail:
        engine = cand
        break
if engine is None:
    print("FAIL: no EEVEE engine in this build")
    sys.exit(3)
scene.render.engine = engine
print("USING ENGINE:", engine)

# Default startup scene already has a cube + camera + light. Keep it tiny + fast.
scene.render.resolution_x = 256
scene.render.resolution_y = 256
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = OUT
if os.path.exists(OUT):
    os.remove(OUT)

try:
    bpy.ops.render.render(write_still=True)
except Exception as e:
    print("RENDER RAISED:", repr(e))
    sys.exit(4)

if not os.path.exists(OUT):
    print("FAIL: no output file written")
    sys.exit(5)

# Non-black check: load the PNG back through bpy (no numpy/PIL dependency) and
# find the max channel value across all pixels.
img = bpy.data.images.load(OUT)
px = img.pixels[:]  # flat RGBA floats 0..1
mx = max(px) if px else 0.0
nonzero = sum(1 for v in px if v > 0.02)
print("OUTPUT:", OUT, "size_bytes=", os.path.getsize(OUT))
print("PIXEL max=%.4f nonzero_frac=%.4f" % (mx, nonzero / max(1, len(px))))
if mx < 0.02:
    print("FAIL: image is essentially black (rendered but empty context?)")
    sys.exit(6)
print("PASS: EEVEE headless render produced a non-black image")
