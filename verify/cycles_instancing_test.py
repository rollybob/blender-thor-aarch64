# GPU vs CPU check for objects Cycles keeps INSTANCED (not baked into the scene BVH): linked duplicates,
# object motion blur, subsurface-scattering materials. The first 5.2.2 build of this recipe rendered all of
# them INVISIBLE on CUDA (GCC 14 aarch64 miscompile in BVH2::pack_instances, fixed by PATCHES/0009).
# Each case renders floor + one test object on GPU (CUDA) and CPU; coverage = fraction of pixels the object
# changes vs a floor-only render. A case FAILS if CPU sees the object but GPU coverage is < 25% of CPU's.
#   blender -b --factory-startup -P verify/cycles_instancing_test.py
# Prints RESULT: OK (exit 0) or RESULT: FAIL (exit 1).
import os
import sys
import tempfile

import bpy
import numpy as np

OUT = tempfile.mkdtemp(prefix="cycles_instancing_")


def scene_base():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.render.resolution_x, sc.render.resolution_y = 320, 180
    sc.cycles.samples = 8
    sc.cycles.use_denoising = False
    sc.cycles.use_adaptive_sampling = False
    w = bpy.data.worlds.new("w")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.3, 0.3, 0.3, 1)
    sc.world = w
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.location = (0, -6, 1.5)
    cam.rotation_euler = (1.45, 0, 0)
    bpy.ops.mesh.primitive_plane_add(size=40)
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sc.collection.objects.link(sun)
    sun.rotation_euler = (0.5, 0.3, 0)
    return sc


def red(**kw):
    m = bpy.data.materials.new("m")
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (0.9, 0.1, 0.1, 1)
    for k, v in kw.items():
        p.inputs[k].default_value = v
    return m


def monkey(mat=None, loc=(0, 0, 1)):
    bpy.ops.mesh.primitive_monkey_add(size=1.5, location=loc)
    ob = bpy.context.active_object
    ob.data.materials.append(mat or red())
    return ob


def case_plain(sc):
    monkey()


def case_linked(sc):
    a = monkey(loc=(-0.9, 0, 1))
    b = bpy.data.objects.new("dup", a.data)
    sc.collection.objects.link(b)
    b.location = (0.9, 0, 1)


def case_motion(sc):
    ob = monkey()
    sc.render.use_motion_blur = True
    for f, x in ((0, -0.2), (2, 0.2)):
        ob.location.x = x
        ob.keyframe_insert("location", frame=f)
    sc.frame_set(1)


def case_sss(sc):
    monkey(red(**{"Subsurface Weight": 1.0, "Subsurface Scale": 0.1}))


def render(dev):
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "CUDA"
    prefs.refresh_devices()
    for d in prefs.devices:
        d.use = (d.type == "CUDA")
    if dev == "GPU" and not any(d.type == "CUDA" for d in prefs.devices):
        print("RESULT: NO_CUDA_DEVICE")
        sys.exit(2)
    sc = bpy.context.scene
    sc.cycles.device = dev
    path = os.path.join(OUT, "r.png")
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = path
    sc.render.use_file_extension = False
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(path)
    a = np.array(im.pixels[:], np.float32).reshape(im.size[1], im.size[0], 4)[..., :3]
    bpy.data.images.remove(im)
    return a


base = {}
for dev in ("GPU", "CPU"):
    scene_base()
    base[dev] = render(dev)

failed = []
for name, build in (("plain", case_plain), ("linked", case_linked), ("motion", case_motion), ("sss", case_sss)):
    cov = {}
    for dev in ("GPU", "CPU"):
        build(scene_base())
        cov[dev] = float((np.abs(render(dev) - base[dev]).max(axis=2) > 0.08).mean())
    ok = not (cov["CPU"] > 0.01 and cov["GPU"] < 0.25 * cov["CPU"])
    print(f"CASE {name:7s} coverage GPU {cov['GPU']:.3f}  CPU {cov['CPU']:.3f}  {'ok' if ok else 'MISSING ON GPU'}")
    if not ok:
        failed.append(name)

print("RESULT:", "OK" if not failed else f"FAIL {failed}")
sys.exit(1 if failed else 0)
