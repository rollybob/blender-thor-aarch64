import bpy, time, sys

scene = bpy.context.scene
scene.render.engine = 'CYCLES'

prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'CUDA'
prefs.refresh_devices()
for d in prefs.devices:
    d.use = (d.type == 'CUDA')
cuda = [d for d in prefs.devices if d.type == 'CUDA']
print('CUDA_DEVICES:', [(d.name, d.use) for d in prefs.devices if d.type == 'CUDA'])
if not cuda:
    print('RESULT: NO_CUDA_DEVICE'); sys.exit(2)

scene.cycles.device = 'GPU'
scene.cycles.samples = 16
scene.render.resolution_x = 256
scene.render.resolution_y = 256
scene.cycles.use_denoising = True
scene.cycles.denoiser = 'OPENIMAGEDENOISE'

if not any(o.type == 'LIGHT' for o in bpy.data.objects):
    bpy.ops.object.light_add(type='SUN')
if not scene.camera:
    bpy.ops.object.camera_add(location=(6, -6, 4), rotation=(1.1, 0, 0.8))
    scene.camera = bpy.context.object

out = '/tmp/cycles_gpu_test.png'
scene.render.filepath = out
scene.render.image_settings.file_format = 'PNG'

t0 = time.time()
bpy.ops.render.render(write_still=True)
dt = time.time() - t0
print(f'RENDER_DONE device={scene.cycles.device} time={dt:.2f}s out={out}')

img = bpy.data.images.load(out)
px = img.pixels[:]
n = len(px)
mx = max(px)
mean = sum(px) / n if n else 0
print(f'PIXEL_STATS n={n} max={mx:.4f} mean={mean:.5f}')
print('RESULT:', 'NONBLACK_OK' if mx > 0.01 else 'BLACK_FAIL')
