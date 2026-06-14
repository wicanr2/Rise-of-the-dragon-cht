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

/* libretro.h typedefs the CALLBACKS but not the core entry points -> declare them. */
typedef void (*fn_void)(void);
typedef unsigned (*fn_uint)(void);
typedef void (*fn_psi)(struct retro_system_info *);
typedef void (*fn_psav)(struct retro_system_av_info *);
typedef void (*fn_env)(retro_environment_t);
typedef void (*fn_video)(retro_video_refresh_t);
typedef void (*fn_asample)(retro_audio_sample_t);
typedef void (*fn_abatch)(retro_audio_sample_batch_t);
typedef void (*fn_ipoll)(retro_input_poll_t);
typedef void (*fn_istate)(retro_input_state_t);
typedef bool (*fn_loadgame)(const struct retro_game_info *);

static fn_void   p_init, p_deinit, p_unload_game, p_run;
static fn_uint   p_api_version;
static fn_psi    p_get_system_info;
static fn_psav   p_get_system_av_info;
static fn_env    p_set_environment;
static fn_video  p_set_video_refresh;
static fn_asample p_set_audio_sample;
static fn_abatch p_set_audio_sample_batch;
static fn_ipoll  p_set_input_poll;
static fn_istate p_set_input_state;
static fn_loadgame p_load_game;
typedef void *(*fn_getmem)(unsigned);
typedef size_t (*fn_getmemsz)(unsigned);
static fn_getmem   p_get_memory_data;
static fn_getmemsz p_get_memory_size;
typedef bool (*fn_unser)(const void *, size_t);
typedef size_t (*fn_sersz)(void);
static fn_unser p_unserialize;
static fn_sersz p_serialize_size;
#define RETRO_MEMORY_VIDEO_RAM 3

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
static unsigned g_input_after = 1500; /* press START only at/after the title screen */
static int16_t input_state_cb(unsigned port, unsigned device, unsigned index, unsigned id) {
    if (port != 0 || device != RETRO_DEVICE_JOYPAD) return 0;
    (void)index;
    /* press START only inside a window [input_after, input_after+700] to start the
     * game past the title/license/loading; then go hands-off so dialogues linger. */
    /* Sequence to reach the apartment: START at title, then navigate the
     * SKIP/PLAY INTRODUCTION choice to SKIP. Genesis C = RETRO_DEVICE_ID_JOYPAD_A.
     * Frames relative to g_input_after (the title-screen frame). */
    unsigned f = (g_frame >= g_input_after) ? g_frame - g_input_after : 999999;
    int pulse = (f % 70) < 5; /* tap, not hold */
    /* Reach the apartment: (1) START at BIOS press-start to boot the CD; (2) START at the
     * game title to begin -> the SKIP/CONTINUE choice appears; (3) press an ACTION button
     * (Genesis A/B/C = libretro Y/B/A) to confirm SKIP (default). Then hands-off so Blade's
     * opening monologue lingers. */
    /* Boot sequence (Mega-CD BIOS is multi-menu): START repeatedly navigates
     * press-start -> BIOS control panel (CD-ROM) -> game title -> intro. To SKIP to the
     * apartment instead of playing the intro, the SKIP/CONTINUE choice (right after the
     * title) needs an ACTION button (A/B/C), not START -- but isolating that single moment
     * blind is unreliable; see docs/SEGACD_RE_NOTES.md. Default here just reaches gameplay. */
    /* Deliberate per-menu navigation (each menu waits for input):
     *  f[0,150]   START   : BIOS press-start -> control panel
     *  f[300,460] C(=A)   : control panel -> select CD-ROM -> boot game
     *  f[1150,1230] START : game title -> SKIP/CONTINUE choice
     *  f[1300,1800] A/B/C : confirm SKIP -> apartment */
    if (id == RETRO_DEVICE_ID_JOYPAD_START &&
        ((f < 150) || (f >= 1250 && f < 1450)) && (f % 130) < 5)
        return 1;
    if (id == RETRO_DEVICE_ID_JOYPAD_A && f >= 300 && f < 460 && pulse)
        return 1;
    if ((id == RETRO_DEVICE_ID_JOYPAD_Y || id == RETRO_DEVICE_ID_JOYPAD_B ||
         id == RETRO_DEVICE_ID_JOYPAD_A) && f >= 1500 && f < 2400 && pulse)
        return 1;
    return 0;
}

static unsigned long frame_brightness(void) {
    if (!g_fb || !g_w || !g_h) return 0;
    unsigned stride = g_pitch / 4; unsigned long s = 0;
    for (unsigned y = 0; y < g_h; y += 2)
        for (unsigned x = 0; x < g_w; x += 2) {
            uint32_t px = g_fb[y * stride + x];
            s += ((px >> 16) & 0xff) + ((px >> 8) & 0xff) + (px & 0xff); /* luminance ~ R+G+B */
        }
    return s;
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
    if (argc >= 8) g_input_after = (unsigned)atoi(argv[7]); /* frame to start pressing START */

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
    p_get_memory_data = (fn_getmem)dlsym(g_core, "retro_get_memory_data");
    p_get_memory_size = (fn_getmemsz)dlsym(g_core, "retro_get_memory_size");
    p_unserialize = (fn_unser)dlsym(g_core, "retro_unserialize");
    p_serialize_size = (fn_sersz)dlsym(g_core, "retro_serialize_size");
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

    /* If ROTD_STATE is set, load that savestate (must be from the SAME GPGX version).
     * The core needs a few retro_run() ticks before unserialize is accepted. */
    const char *statefile = getenv("ROTD_STATE");
    if (statefile && *statefile && p_unserialize) {
        for (int w = 0; w < 4; w++) p_run();
        FILE *sf = fopen(statefile, "rb");
        if (!sf) { fprintf(stderr, "STATE: cannot open %s\n", statefile); }
        else {
            fseek(sf, 0, SEEK_END); long ssz = ftell(sf); fseek(sf, 0, SEEK_SET);
            void *sbuf = malloc(ssz); fread(sbuf, 1, ssz, sf); fclose(sf);
            size_t need = p_serialize_size ? p_serialize_size() : 0;
            fprintf(stderr, "STATE: file=%ld bytes core-expects=%zu\n", ssz, need);
            bool ok = p_unserialize(sbuf, (size_t)ssz);
            fprintf(stderr, "STATE: unserialize %s\n", ok ? "OK" : "FAILED (version mismatch?)");
            free(sbuf);
        }
    }

    char path[1100];
    for (g_frame = 0; g_frame < frames; g_frame++) {
        p_run();
        unsigned long b = frame_brightness();
        if (every && (g_frame % every) == 0) {
            snprintf(path, sizeof path, "%s/frame_%05u.ppm", outdir, g_frame);
            dump_ppm(path);
        }
        if ((g_frame % 60) == 0)
            fprintf(stderr, "  frame %u/%u  %ux%u brightness=%lu\n", g_frame, frames, g_w, g_h, b);
    }
    snprintf(path, sizeof path, "%s/frame_final.ppm", outdir);
    dump_ppm(path);

    /* Dump VRAM (font tiles live here once the game loads them) for static decoding. */
    if (p_get_memory_data && p_get_memory_size) {
        void *vram = p_get_memory_data(RETRO_MEMORY_VIDEO_RAM);
        size_t vsz = p_get_memory_size(RETRO_MEMORY_VIDEO_RAM);
        fprintf(stderr, "VRAM: data=%p size=%zu\n", vram, vsz);
        if (vram && vsz) {
            snprintf(path, sizeof path, "%s/vram.bin", outdir);
            FILE *vf = fopen(path, "wb");
            if (vf) { fwrite(vram, 1, vsz, vf); fclose(vf); fprintf(stderr, "wrote %s\n", path); }
        }
    }
    fprintf(stderr, "done: %u frames, last fb %ux%u\n", frames, g_w, g_h);
    p_unload_game();
    p_deinit();
    dlclose(g_core);
    return 0;
}
