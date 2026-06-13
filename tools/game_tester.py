#!/usr/bin/env python3
"""Game-tester driver for the ROTD CHT build (WORK IN PROGRESS).

Goal: drive the patched ScummVM through gameplay headlessly to exercise every
dialogue, auto-screenshot the Chinese, and surface localization issues.

How it works
------------
The engine is instrumented (build with `-d2`) to emit, every time an
interactive scene's hotspots change:

    GTSTATE scene=<N> hotspots=<num>:<x>,<y>,<w>,<h>;...

(see DgdsEngine::run() scene branch). It also logs `CJK dialog <scene>:<num>`
whenever a translated dialogue is drawn. This driver:
  1. launches the game under Xvfb at 640x400 (1:1 with the 2x backend),
  2. jumps to a scene via the debugger console (`scene <N>`),
  3. parses GTSTATE for that scene's hotspot rects,
  4. left-clicks each hotspot center (rect_center x2 = screen px) and
     screenshots whatever dialogue fires, correlating with the CJK-dialog log.

KNOWN LIMITATION (blocking full automation)
-------------------------------------------
The intro state machine (REQ skip/play menu -> ADS cutscene -> first SDS scene)
does not cleanly hand off to interactive gameplay under headless control: a
console `scene N` jump loads the scene in engine state, but the intro menu/ADS
overlay persists on screen, so clicks land on the stale menu, not the scene's
hotspots. Cleanly entering gameplay needs an engine-side autopilot that
dismisses the intro and invokes hotspot ops directly (calling
SDSScene::leftButtonAction on a hotspot by _num) instead of via xdotool.
That autopilot is the next step; this file documents the working pieces.

Verified working: scene loads via console (`load scene file S3.SDS`),
GTSTATE reports `scene=3 hotspots=7:229,54,26,25;4:0,180,320,20;3:0,0,320,200`.
"""
import subprocess, time, os, re, sys, signal

SV = os.environ.get("SCUMMVM", "/home/anr2/zak-zh/tools/scummvm-src/scummvm")
GAME = "/home/anr2/rise-of-the-dragon/game_en/riseofthedragon"
OUT = "/home/anr2/rise-of-the-dragon/screenshots/gametest"
DISP = ":99"

def sh(cmd):
    subprocess.run(cmd, shell=True, env={**os.environ, "DISPLAY": DISP},
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def parse_hotspots(line):
    m = re.search(r"GTSTATE scene=(\d+) hotspots=(.*)", line)
    if not m: return None
    scene = int(m.group(1))
    spots = []
    for h in m.group(2).split(";"):
        if not h: continue
        num, rest = h.split(":")
        x, y, w, hh = map(int, rest.split(","))
        spots.append((int(num), x + w // 2, y + hh // 2))  # num, cx, cy (320x200)
    return scene, spots

def run_scene(scene):
    os.makedirs(OUT, exist_ok=True)
    log = f"/tmp/gt_{scene}.log"
    xvfb = subprocess.Popen(["Xvfb", DISP, "-screen", "0", "640x400x24"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    with open(log, "w") as lf:
        sv = subprocess.Popen([SV, "-p", GAME, "-d2", "--fullscreen",
                               "--no-aspect-ratio", "rise"], stdout=lf, stderr=lf,
                              env={**os.environ, "DISPLAY": DISP})
        time.sleep(6)
        # jump into the scene via the debugger console
        sh("xdotool key ctrl+alt+d"); time.sleep(1.5)
        sh(f'xdotool type --delay 80 "scene {scene}"'); sh("xdotool key Return"); time.sleep(1)
        sh('xdotool type --delay 80 "exit"'); sh("xdotool key Return"); time.sleep(3)
        # read hotspots
        spots = None
        for ln in open(log):
            r = parse_hotspots(ln)
            if r and r[0] == scene: spots = r[1]
        print(f"scene {scene}: hotspots = {spots}")
        # click each hotspot (x2 -> screen) and screenshot
        if spots:
            for num, cx, cy in spots:
                sh(f"xdotool mousemove {cx*2} {cy*2} click 1"); time.sleep(1.2)
                sh(f"import -window root {OUT}/s{scene}_h{num}.png")
        sv.send_signal(signal.SIGTERM); time.sleep(1); sv.kill()
    xvfb.terminate()
    dialogs = [l for l in open(log) if "CJK dialog" in l]
    print(f"  CJK dialogs fired: {len(dialogs)}")

if __name__ == "__main__":
    scenes = [int(a) for a in sys.argv[1:]] or [3]
    for s in scenes:
        run_scene(s)
