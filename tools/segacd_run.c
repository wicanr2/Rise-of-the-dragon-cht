/* Minimal headless libretro frontend: boot a Sega CD game in Genesis Plus GX,
 * run N frames feeding a scripted input, and dump selected video frames as PPM.
 * Purpose: capture the OFFICIAL Japanese text by rendering the JP disc, then OCR
 * the frames (sidesteps the custom SD4 text encoding entirely). Host stays clean:
 * built + run inside Docker. No copyrighted data is emitted to git (PPMs are local).
 *
 * Usage: segacd_run <core.so> <game.cue> <system_dir> <out_dir> <frames> <dump_every>
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <dlfcn.h>
#include "libretro.h"

static void *g_core;
static char g_system_dir[1024];
static char g_save_dir[1024];
static const uint32_t *g_fb;       /* latest framebuffer (XRGB8888) */
static unsigned g_w, g_h, g_pitch; /* pitch in bytes */

#define SYM(name) static retro_##name##_t p_##name;
SYM(init) SYM(deinit) SYM(api_version) SYM(get_system_info) SYM(get_system_av_info)
SYM(set_environment) SYM(set_video_refresh) SYM(set_audio_sample) SYM(set_audio_sample_batch)
SYM(set_input_poll) SYM(set_input_state) SYM(load_game) SYM(unload_game) SYM(run)
#undef SYM

static void load_sym(void **dst, const char *name) {
    *dst = dlsym(g_core, name);
    if (!*dst) { fprintf(stderr, "missing symbol %s\n", name); exit(2); }
}

/* ---- libretro callbacks ---- */
static bool env_cb(unsigned cmd, void *data) {
    switch (cmd) {
    case RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY:
        *(const char **)data = g_system_dir; return true;
    case RETRO_ENVIRONMENT_GET_SAVE_DIRECTORY:
        *(const char **)data = g_save_dir; return true;
    case RETRO_ENVIRONMENT_SET_PIXEL_FORMAT: {
        enum retro_pixel_format fmt = *(const enum retro_pixel_format *)data;
        return fmt == RETRO_PIXEL_FORMAT_XRGB8888; /* we request this */
    }
    case RETRO_ENVIRONMENT_GET_VARIABLE: {
        struct retro_variable *v = (struct retro_variable *)data;
        v->value = NULL; /* use core defaults */
        return false;
    }
    case RETRO_ENVIRONMENT_GET_VARIABLE_UPDATE:
        *(bool *)data = false; return true;
    case RETRO_ENVIRONMENT_GET_CAN_DUPE:
        *(bool *)data = true; return true;
    case RETRO_ENVIRONMENT_SET_PERFORMANCE_LEVEL:
    case RETRO_ENVIRONMENT_SET_VARIABLES:
    case RETRO_ENVIRONMENT_SET_CONTROLLER_INFO:
    case RETRO_ENVIRONMENT_SET_SUBSYSTEM_INFO:
    case RETRO_ENVIRONMENT_SET_INPUT_DESCRIPTORS:
    case RETRO_ENVIRONMENT_SET_GEOMETRY:
    case RETRO_ENVIRONMENT_SET_SYSTEM_AV_INFO:
        return true;
    default:
        return false;
    }
}

static void video_cb(const void *data, unsigned width, unsigned height, size_t pitch) {
    if (!data) return; /* dupe frame */
    g_fb = (const uint32_t *)data; g_w = width; g_h = height; g_pitch = (unsigned)pitch;
}
static void audio_sample_cb(int16_t l, int16_t r) { (void)l; (void)r; }
static size_t audio_batch_cb(const int16_t *d, size_t frames) { (void)d; return frames; }
static void input_poll_cb(void) {}

/* Scripted input: press START periodically to advance intro/menus. */
static unsigned g_frame = 0;
static int16_t input_state_cb(unsigned port, unsigned device, unsigned index, unsigned id) {
    (void)port; (void)device; (void)index;
    /* tap START for ~6 frames once every 90 frames to skip intro screens */
    if (id == RETRO_DEVICE_ID_JOYPAD_START && (g_frame % 90) < 6) return 1;
    return 0;
}

static void dump_ppm(const char *path) {
    if (!g_fb || !g_w || !g_h) return;
    FILE *f = fopen(path, "wb");
    if (!f) return;
    fprintf(f, "P6\n%u %u\n255\n", g_w, g_h);
    unsigned stride = g_pitch / 4;
    for (unsigned y = 0; y < g_h; y++) {
        for (unsigned x = 0; x < g_w; x++) {
            uint32_t px = g_fb[y * stride + x];
            unsigned char rgb[3] = { (px >> 16) & 0xff, (px >> 8) & 0xff, px & 0xff };
            fwrite(rgb, 1, 3, f);
        }
    }
    fclose(f);
}

int main(int argc, char **argv) {
    if (argc < 7) { fprintf(stderr, "usage: %s core game sysdir outdir frames every\n", argv[0]); return 1; }
    const char *core = argv[1], *game = argv[2], *outdir = argv[4];
    snprintf(g_system_dir, sizeof g_system_dir, "%s", argv[3]);
    snprintf(g_save_dir, sizeof g_save_dir, "%s", argv[3]);
    unsigned frames = (unsigned)atoi(argv[5]), every = (unsigned)atoi(argv[6]);

    g_core = dlopen(core, RTLD_NOW);
    if (!g_core) { fprintf(stderr, "dlopen: %s\n", dlerror()); return 2; }
    load_sym((void **)&p_init, "retro_init");
    load_sym((void **)&p_deinit, "retro_deinit");
    load_sym((void **)&p_api_version, "retro_api_version");
    load_sym((void **)&p_get_system_info, "retro_get_system_info");
    load_sym((void **)&p_get_system_av_info, "retro_get_system_av_info");
    load_sym((void **)&p_set_environment, "retro_set_environment");
    load_sym((void **)&p_set_video_refresh, "retro_set_video_refresh");
    load_sym((void **)&p_set_audio_sample, "retro_set_audio_sample");
    load_sym((void **)&p_set_audio_sample_batch, "retro_set_audio_sample_batch");
    load_sym((void **)&p_set_input_poll, "retro_set_input_poll");
    load_sym((void **)&p_set_input_state, "retro_set_input_state");
    load_sym((void **)&p_load_game, "retro_load_game");
    load_sym((void **)&p_unload_game, "retro_unload_game");
    load_sym((void **)&p_run, "retro_run");

    fprintf(stderr, "libretro api %u\n", p_api_version());
    p_set_environment(env_cb);
    p_set_video_refresh(video_cb);
    p_set_audio_sample(audio_sample_cb);
    p_set_audio_sample_batch(audio_batch_cb);
    p_set_input_poll(input_poll_cb);
    p_set_input_state(input_state_cb);
    p_init();

    struct retro_system_info si; memset(&si, 0, sizeof si);
    p_get_system_info(&si);
    fprintf(stderr, "core: %s %s\n", si.library_name ? si.library_name : "?", si.library_version ? si.library_version : "?");

    struct retro_game_info gi; memset(&gi, 0, sizeof gi);
    gi.path = game; gi.data = NULL; gi.size = 0; /* full-path content; core reads the cue */
    if (!p_load_game(&gi)) { fprintf(stderr, "load_game FAILED\n"); return 3; }

    struct retro_system_av_info av; memset(&av, 0, sizeof av);
    p_get_system_av_info(&av);
    fprintf(stderr, "av: base %ux%u max %ux%u fps %.2f\n",
            av.geometry.base_width, av.geometry.base_height,
            av.geometry.max_width, av.geometry.max_height, av.timing.fps);

    char path[1100];
    for (g_frame = 0; g_frame < frames; g_frame++) {
        p_run();
        if (every && (g_frame % every) == 0) {
            snprintf(path, sizeof path, "%s/frame_%05u.ppm", outdir, g_frame);
            dump_ppm(path);
        }
    }
    snprintf(path, sizeof path, "%s/frame_final.ppm", outdir);
    dump_ppm(path);
    fprintf(stderr, "done: %u frames, last fb %ux%u\n", frames, g_w, g_h);
    p_unload_game();
    p_deinit();
    dlclose(g_core);
    return 0;
}
