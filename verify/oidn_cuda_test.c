/* GPU-OIDN verification for the Thor aarch64 Blender deps.
 * Uses OIDN's own C API to (1) enumerate physical devices and confirm a CUDA
 * device is present, (2) create + commit a CUDA device, (3) run an RT denoise
 * on Thor's GPU. Step 3 forces the sm_110 CUDA cubin to load + execute -- if the
 * arch fixups were wrong we'd get "no kernel image available for execution".
 */
#include <OpenImageDenoise/oidn.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>

int main(void) {
  /* 1. Enumerate physical devices */
  int n = oidnGetNumPhysicalDevices();
  printf("PHYSICAL_DEVICES=%d\n", n);
  int cuda_found = 0;
  for (int i = 0; i < n; i++) {
    int type = oidnGetPhysicalDeviceInt(i, "type");
    const char *name = oidnGetPhysicalDeviceString(i, "name");
    printf("  dev[%d] type=%d name=%s\n", i, type, name ? name : "?");
    if (type == OIDN_DEVICE_TYPE_CUDA) cuda_found = 1;
  }
  printf("CUDA_PHYSICAL_DEVICE=%s\n", cuda_found ? "YES" : "NO");

  /* 2. Create + commit a CUDA device explicitly */
  OIDNDevice device = oidnNewDevice(OIDN_DEVICE_TYPE_CUDA);
  if (!device) { printf("RESULT: OIDN_CUDA_FAIL (oidnNewDevice=null)\n"); return 2; }
  oidnCommitDevice(device);
  const char *err = NULL;
  if (oidnGetDeviceError(device, &err) != OIDN_ERROR_NONE) {
    printf("RESULT: OIDN_CUDA_FAIL (commit: %s)\n", err ? err : "?"); return 3;
  }
  printf("CUDA_DEVICE_COMMITTED ok\n");

  /* 3. Minimal RT denoise -> exercises the sm_110 cubin on Thor */
  const int W = 128, H = 128;
  const size_t sz = (size_t)W * H * 3 * sizeof(float);
  OIDNBuffer color = oidnNewBuffer(device, sz);
  OIDNBuffer output = oidnNewBuffer(device, sz);
  float *host = (float *)malloc(sz);
  for (int i = 0; i < W * H * 3; i++)
    host[i] = ((i * 2654435761u) & 0xffff) / 65535.0f; /* noisy pattern */
  oidnWriteBuffer(color, 0, sz, host);

  OIDNFilter filter = oidnNewFilter(device, "RT");
  oidnSetFilterImage(filter, "color", color, OIDN_FORMAT_FLOAT3, W, H, 0, 0, 0);
  oidnSetFilterImage(filter, "output", output, OIDN_FORMAT_FLOAT3, W, H, 0, 0, 0);
  oidnSetFilterBool(filter, "hdr", false);
  oidnCommitFilter(filter);
  oidnExecuteFilter(filter);
  if (oidnGetDeviceError(device, &err) != OIDN_ERROR_NONE) {
    printf("RESULT: OIDN_CUDA_FAIL (execute: %s)\n", err ? err : "?"); return 4;
  }

  float *out = (float *)malloc(sz);
  oidnReadBuffer(output, 0, sz, out);
  double s = 0; int nonzero = 0;
  for (int i = 0; i < W * H * 3; i++) { s += out[i]; if (out[i] != 0.0f) nonzero++; }
  printf("DENOISE_OUT mean=%.5f nonzero=%d/%d\n", s / (W * H * 3), nonzero, W * H * 3);
  printf("RESULT: %s\n", (nonzero > 0) ? "OIDN_CUDA_OK" : "OIDN_CUDA_FAIL");

  oidnReleaseFilter(filter);
  oidnReleaseBuffer(color);
  oidnReleaseBuffer(output);
  oidnReleaseDevice(device);
  free(host); free(out);
  return 0;
}
