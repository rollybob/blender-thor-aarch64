// GCC 14.1/14.2 aarch64 miscompile (fixed in GCC >= 14.3), reduced from Blender 5.2.2 Cycles BVH2::pack_instances (intern/cycles/bvh/bvh2.cpp).
// int4 mirrors Cycles' util/types_int4.h on aarch64 (sse2neon: __m128i == int64x2_t) -- a union of a NEON vector and
// four ints, whose copy assignment copies the vector member. Patching .x/.y of a copy and storing it must keep .z/.w.
#include <arm_neon.h>
#include <cstddef>
#include <cstdio>

struct alignas(16) int4 {
  union {
    int64x2_t m128;
    struct {
      int x, y, z, w;
    };
  };
  int4() = default;
  int4(const int4 &a) = default;
  int4 &operator=(const int4 &a)
  {
    m128 = a.m128;
    return *this;
  }
};

__attribute__((noinline)) void merge(int4 *dst, const int4 *src, size_t n, size_t offset)
{
  for (size_t i = 0; i < n; i++) {
    int4 data = src[i];
    data.x += offset;
    data.y += offset;
    dst[i] = data;
  }
}

int main()
{
  int4 src[4], dst[4];
  for (int i = 0; i < 4; i++) {
    src[i].x = i;
    src[i].y = i + 1;
    src[i].z = 0x7f;  // visibility in Cycles
    src[i].w = 1;     // primitive type in Cycles
  }
  merge(dst, src, 4, 100);
  int bad = 0;
  for (int i = 0; i < 4; i++) {
    std::printf("dst[%d] = {%d, %d, %d, %d}\n", i, dst[i].x, dst[i].y, dst[i].z, dst[i].w);
    bad |= dst[i].x != i + 100 || dst[i].y != i + 101 || dst[i].z != 0x7f || dst[i].w != 1;
  }
  std::puts(bad ? "FAIL: .z/.w lost" : "OK");
  return bad;
}
