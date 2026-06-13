#!/usr/bin/env python3
"""Generate a Markdown QA report from a game-tester (autopilot) run.

Reads:
  - an autopilot script (the test plan: scene/look/use/shot/lang/wait/quit lines)
  - the engine log (for `shot` confirmations + `hot area N not found` / warnings)
  - the screenshots directory (autopilot_shots/ by default)
Writes a report mapping every screenshot to its scene/action/display-mode, flags
missing hot-areas or shots, and embeds thumbnails for human review of the CJK
layout. Does NOT reproduce game dialogue text — only scene:num keys + images.

Usage: game_test_report.py autopilot.txt /tmp/sv_run.log autopilot_shots docs/GAME_TEST_REPORT.md
Reusable for any ScummVM AVG localization QA.
"""
import sys, os, re

MODE = {0: "英文 (original)", 1: "中文 24×24", 2: "中文 16×16", 3: "德文", 4: "日文"}

def main():
    script, logp, shotsdir, outp = sys.argv[1:5]
    steps = [l.strip() for l in open(script) if l.strip() and not l.startswith("#")]
    log = open(logp, encoding="latin1").read() if os.path.exists(logp) else ""

    scene = "?"
    mode = 1  # default 中文24
    rows = []
    for s in steps:
        parts = s.split()
        op = parts[0]
        arg = parts[1] if len(parts) > 1 else ""
        if op == "scene":
            scene = arg
        elif op == "lang":
            mode = int(arg)
        elif op in ("look", "use"):
            rows.append({"kind": "act", "scene": scene, "mode": mode, "action": f"{op} {arg}", "shot": None})
        elif op == "shot":
            # attach to the most recent action, or a standalone capture
            shotfile = f"{arg}.png"
            exists = os.path.exists(os.path.join(shotsdir, shotfile))
            if rows and rows[-1]["kind"] == "act" and rows[-1]["shot"] is None:
                rows[-1]["shot"] = shotfile
                rows[-1]["scene"] = scene
                rows[-1]["mode"] = mode
                rows[-1]["exists"] = exists
            else:
                rows.append({"kind": "act", "scene": scene, "mode": mode, "action": "(state)",
                             "shot": shotfile, "exists": exists})

    missing = sorted(set(re.findall(r"hot area (\d+) not found", log)))
    nshots = sum(1 for r in rows if r.get("shot"))
    scenes = sorted({r["scene"] for r in rows}, key=lambda s: int(re.sub(r"\D", "", s) or 0))

    out = []
    out.append("# Game Test Report — Rise of the Dragon 繁體中文化\n")
    out.append("由引擎內建 autopilot（game-tester）自動跑出。每格截圖是該場景某句台詞在某顯示模式下的實機畫面，供人工檢查中文排版/斷行/溢出。\n")
    out.append("## 摘要\n")
    out.append(f"- 測試場景：{', '.join(scenes)}")
    out.append(f"- 截圖數：{nshots}")
    out.append(f"- 顯示模式涵蓋：{', '.join(sorted({MODE[r['mode']] for r in rows}))}")
    out.append(f"- 找不到的熱區：{', '.join(missing) if missing else '無'}\n")
    out.append("## 逐項截圖\n")
    out.append("| # | 場景 | 動作 | 顯示模式 | 截圖 | 狀態 |")
    out.append("|---|---|---|---|---|---|")
    i = 0
    for r in rows:
        if not r.get("shot"):
            continue
        i += 1
        ok = "✅" if r.get("exists") else "⚠️ 缺檔"
        img = f"![]({os.path.relpath(os.path.join(shotsdir, r['shot']), os.path.dirname(outp))})" if r.get("exists") else "—"
        out.append(f"| {i} | {r['scene']} | `{r['action']}` | {MODE[r['mode']]} | {img} | {ok} |")
    out.append("\n> 截圖在完整 QA run 會產生於 `autopilot_shots/`（gitignored，本地重跑）；本報告示意用 `screenshots/showcase/` 的代表圖。")
    os.makedirs(os.path.dirname(outp), exist_ok=True)
    open(outp, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print(f"# wrote {outp}: {nshots} shots, {len(scenes)} scenes, missing={missing}")

if __name__ == "__main__":
    main()
