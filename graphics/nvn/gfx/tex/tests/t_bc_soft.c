// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 S2Arm contributors
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../nvn_bc_soft.h"
#include "../nvn_fmt_mtl.h"

static unsigned bits(const uint8_t *p, unsigned pos, unsigned n) {
    unsigned v = 0;
    for (unsigned i = 0; i < n; i++) v |= ((p[(pos + i) >> 3] >> ((pos + i) & 7)) & 1u) << i;
    return v;
}

int main(void) {
    static const struct { uint32_t nvn, mtl; } formats[] = {
        {0x41,130},{0x42,130},{0x43,132},{0x44,134},
        {0x45,131},{0x46,131},{0x47,133},{0x48,135},
        {0x49,140},{0x4a,141},{0x4b,142},{0x4c,143},
        {0x4d,152},{0x4e,153},{0x4f,150},{0x50,151}
    };
    for (size_t i = 0; i < sizeof formats / sizeof formats[0]; i++) {
        uint32_t original = 0, canonical = 0;
        assert(nvn_fmt_bc_mtl(formats[i].nvn, &original));
        assert(nvn_fmt_to_mtl((int)formats[i].nvn, &canonical, NULL) == 1);
        assert(original == formats[i].mtl && canonical == original);
    }
    assert(!nvn_fmt_bc_mtl(0x40, NULL));
    assert(!nvn_fmt_bc_mtl(0x51, NULL));
    static const struct { uint32_t pf, astc, plain, block; int bpp_astc, bpp_plain; } cases[] = {
        {130,204,70,8,4,4}, {131,186,71,8,4,4},
        {132,204,70,16,4,4}, {133,186,71,16,4,4},
        {134,204,70,16,4,4}, {135,186,71,16,4,4},
        {140,10,10,8,1,1}, {141,12,12,8,1,1},
        {142,30,30,16,2,2}, {143,32,32,16,2,2},
        {150,115,115,16,8,8}, {151,92,115,16,4,8},
        {152,204,70,16,4,4}, {153,186,71,16,4,4}
    };
    nvn_bc_astc = 1;
    for (size_t i = 0; i < sizeof cases / sizeof cases[0]; i++) {
        int bpp = 0;
        assert(bc_soft_target(cases[i].pf, &bpp) == cases[i].astc);
        assert(bpp == cases[i].bpp_astc);
        size_t rows = bc_soft_rows(cases[i].pf, 5);
        assert(rows == (cases[i].astc == 204 || cases[i].astc == 186 ? 2u : 8u));

        uint8_t src[64] = {0};
        size_t src_pitch = 2u * cases[i].block;
        size_t dst_pitch = 2u * 4u * (size_t)bpp;
        uint8_t *dst = (uint8_t *)malloc(dst_pitch * rows);
        assert(dst);
        memset(dst, 0xA5, dst_pitch * rows);
        assert(bc_soft_decode(cases[i].pf, src, src_pitch, 5, 5, dst, dst_pitch) == 0);
        free(dst);
    }

    // BC1 four-colour mode must retain the two RGB565 palette endpoints exactly in ASTC.
    {
        uint8_t bc1[8] = {0x00,0xF8, 0xE0,0x07, 0,0,0,0}; // red > green, all texels select endpoint 0
        uint8_t astc[16] = {0};
        assert(bc_soft_out_block(130, bc1, astc, 16) == 0);
        assert(bits(astc, 0, 11) == 0x42);
        assert(bits(astc, 13, 4) == 8);  // CEM 8, RGB direct
        assert(bits(astc, 17, 8) == 255 && bits(astc, 25, 8) == 0);
        assert(bits(astc, 33, 8) == 0 && bits(astc, 41, 8) == 255);
        assert(bits(astc, 49, 8) == 0 && bits(astc, 57, 8) == 0);
    }

    // The explicit opt-out returns the legacy uncompressed targets.
    nvn_bc_astc = 0;
    for (size_t i = 0; i < sizeof cases / sizeof cases[0]; i++) {
        int bpp = 0;
        assert(bc_soft_target(cases[i].pf, &bpp) == cases[i].plain);
        assert(bpp == cases[i].bpp_plain);
    }
    puts("t_bc_soft: all BC1–BC7 target, edge-layout, BC1-palette and opt-out checks passed");
    return 0;
}
