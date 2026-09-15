# Confirms Cycles uses GPU-OIDN (OIDN CUDA device) on Thor, not CPU-OIDN.
# Renders on the CUDA device with OpenImageDenoise + denoising_use_gpu=True.
# Run with OIDN_VERBOSE=2 in the environment: OIDN prints its device banner when the
# denoiser device is created -- "Type: CUDA / NVIDIA Thor" proves GPU-OIDN engaged.
import bpy, time, sys

scene = bpy.context.scene
scene.render.engine = 'CYCLES'

prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'CUDA'
prefs.refresh_devices()
for d in prefs.devices:
    d.use = (d.type == 'CUDA')
if not any(d.type == 'CUDA' for d in prefs.devices):
    print('RESULT: NO_CUDA_DEVICE'); sys.exit(2)

scene.cycles.device = 'GPU'
scene.cycles.samples = 16
scene.render.resolution_x = 256
scene.render.resolution_y = 256
scene.cycles.use_denoising = True
scene.cycles.denoiser = 'OPENIMAGEDENOISE'

# Route OIDN to the GPU (robust to property presence across versions).
if hasattr(scene.cycles, 'denoising_use_gpu'):
    scene.cycles.denoising_use_gpu = True
    print('DENOISING_USE_GPU:', scene.cycles.denoising_use_gpu)
else:
    print('DENOISING_USE_GPU: property-absent')

if not any(o.type == 'LIGHT' for o in bpy.data.objects):
    bpy.ops.object.light_add(type='SUN')
if not scene.camera:
    bpy.ops.object.camera_add(location=(6, -6, 4), rotation=(1.1, 0, 0.8))
    scene.camera = bpy.context.object

out = '/tmp/cycles_oidn_gpu_test.png'
scene.render.filepath = out
scene.render.image_settings.file_format = 'PNG'

t0 = time.time()
bpy.ops.render.render(write_still=True)
dt = time.time() - t0
print(f'RENDER_DONE device={scene.cycles.device} denoise_gpu={getattr(scene.cycles,"denoising_use_gpu","?")} time={dt:.2f}s')

img = bpy.data.images.load(out)
px = img.pixels[:]
mx = max(px)
mean = sum(px) / len(px)
print(f'PIXEL_STATS max={mx:.4f} mean={mean:.5f}')
print('RESULT:', 'NONBLACK_OK' if mx > 0.01 else 'BLACK_FAIL')
