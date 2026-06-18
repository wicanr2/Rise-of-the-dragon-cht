---
name: rise-of-the-dragon-cht
description: 把 ScummVM DGDS 引擎遊戲（Rise of the Dragon / Heart of China / Willy Beamish）做繁體中文化 + 全平台打包的完整 SOP。當使用者談到「Rise of the Dragon」「火龍之吼」「孟波」「DGDS 中文化」「ScummVM dgds CJK」「TTM 字串」「STORE AREA」「電腦/視訊電話畫面英文」「捷運站名沒翻」「對話名牌英文」「Android APK 注入遊戲」「liboboe.so not found」「eglCreateWindowSurface」「全平台 FULL 打包」「dist-all 重打包」「片頭標題加中文/中文副標」「中國之心/威利奇遇記 title」「drawTitleSubtitle」「毛筆/楷書/草書字型繁體國覆蓋」「日文字幕模式/F8 日文」「Shift-JIS 點陣字」「Big5+SJIS 第二編碼字型」「whisper 聽寫日配/Sega CD 語音字幕」等情境觸發。
---

> 📌 這份是 Claude Code skill `rise-of-the-dragon-cht` 的 repo 內鏡像（source of truth 在 `~/.claude/skills/rise-of-the-dragon-cht/SKILL.md`），隨 dev-setup 一起打包,讓在他機重建專案的人也拿得到完整 SOP。上方 `name`/`description` frontmatter 是 skill 觸發用,當文件讀即可。

# Rise of the Dragon（ScummVM DGDS）繁中化 + 全平台 ship 完整 SOP

DGDS 引擎老遊戲（Dynamix 1990）的中文化。引擎走 **engine-side overlay**（不改遊戲資料，patch ScummVM 在繪字處攔截 → 查表 → 用點陣 CJK 字型重畫到 hi-res 疊圖層）。本 skill 記下所有**非顯然**的關鍵點，尤其 TTM 持久層那段是反覆踩坑換來的。

Repo: `git@github.com:wicanr2/Rise-of-the-dragon-cht.git`。patch base = ScummVM commit `f4526cf`，所有引擎改動是 `patches/dgds-cjk.patch`（從本地 scummvm-src 工作樹 `git diff HEAD -- engines/dgds/` 重產）。

## 0. 三層 voice / 三個產物

- **資料**：`translations/zh.json`（UTF-8）→ `tools/build_translation.py` → `build/zh.dtr`（DTRN，Big5）。**純資料,改完只要重建 zh.dtr 重新部署各平台,免重編引擎。**
- **字型**：`tools/build_cjk_font.py` → `dragon_zh{12,16,24}.dcjk`（點陣字）。
- **引擎**：`patches/dgds-cjk.patch`（engines/dgds/*）。**改引擎才要重編全平台。**

## 1. 三條繪字路徑（各自的 CJK hook）── 最重要

DGDS 有三條獨立的玩家可見文字路徑,**漏一條就有英文殘留**:

| 路徑 | 來源 | hook | 查表 |
|---|---|---|---|
| **對話內文** | SDS scene dialog | `dialog.cpp` `drawForeground` | `lookupDialog(scene, num)` 鍵 `"<scene>:<num>"` |
| **對話名牌 / 選單 / REQ 標題** | dialog title（冒號前）/ menu / request header | `request.cpp` `drawHeader` | `lookupUI(header)` 鍵 `"UI:"+trim` |
| **TTM 畫面文字**（電腦/視訊電話/捷運/保全鍵盤）| TTM script drawString op `0xa2X0` | `ttm.cpp` 該 case | `lookupUI(str)` 鍵 `"UI:"+trim` |

- **對話名牌**（KARYN / MAYOR VINCENZI）= `drawType2` 取 `_str` 冒號前當 title,**用英文原字串**。但 `drawHeader` 已有 `lookupUI(header)` hook → 只要 zh.json 補 `"UI:<英文名牌>"` 就會中文化（**純資料**）。名牌一律大寫,鍵也要大寫。
- 撈所有名牌:解析 `dialogs_en.json`（list of {scene,num,text}）每筆 text 的「冒號緊接 `\r`」→ 冒號前即 title。ROTD 有 84 個。

## 2. TTM 字串靜態抽取（不要瞎玩遊戲找字）

`tools/extract_ttm_strings.py`：用 `tools/dgds_volume.py --extract` 抽出所有資源 → 每個 `.ttm` 的 **`TT3:` chunk**（script,需 `dgds_chunks.decompress_blob`）→ 逐 op 走訪,`code & 0xFFF0 == 0xf100..0xf190`（SET STRING 0-9）即顯示字串。

- TTM op 格式:`op = code & 0xFFF0`,`count = code & 0x000F`。`count==0x0F` → 字串運算元（null-terminated,**偶數對齊**,讀完補 1 byte 若奇數）；特例 `0xaf1f/0xaf2f` 是點列表。否則 `count` 個 u16。
- **`TAG:` chunk = 內部 frame 標籤（"City Hall Label"）不要抽**,只抽 `TT3:`。
- 抽完 diff 掉 zh.json 已有的 `UI:` 鍵 → 缺的一次補齊。ROTD 補了 44 條（Chen Lu 電話大寫 `TO:    CHEN LU`、捷運站名拆字 City/Hall、`Select:` 聯絡人選單、保全鍵盤、ID 卡提示）。
- **空格要逐字對**:`"UI:To:    William Hunter"`（4 空格）`"UI:From:  Mayor Vincenzi"`（2 空格）—— lookupUI 只 trim 頭尾,內部空格保留。

## 3. TTM 持久層 ── 最難的坑（STORE AREA 模型）

TTM 畫面文字**畫一次然後 ADS hold**（不像對話框每幀重畫）。英文持久是靠 **STORE AREA op `0x4200`** 把 composition 區域存進 `_storedAreaBuffer`，每幀 transBlit 回來。CJK 是 hi-res overlay（present 時最後畫）→ 跟 stored-area 像素模型不同步,衍生一連串症狀:

| 症狀 | 錯誤做法 | 正解 |
|---|---|---|
| 訊息**閃一幀就消失** | overlay 每幀被 `clearDeferred()` 清 | 獨立持久層 `_deferredBg`（per-frame clear 不碰它）|
| 切 NEXT/PREV **多則疊加** | `_deferredBg` 只累加 | 每行帶 `committed` 旗標 |
| 切到頭像/關閉**舊文字殘留** | 換場景才清 | STORE AREA → `commitBg(rect)` |
| PLAY 播放動畫**標題浮在臉上** | 只 hook ttm.cpp STORE AREA | 也要 hook talking-head |

**最終模型**（cjk.h/cpp + ttm.cpp + head.cpp + dgds.cpp）:
- `deferLine(..., persist=true)` → `_deferredBg`（committed=false）,立即顯示且持久。
- `commitBg(rect)`（ttm.cpp `0x4200` STORE AREA 呼叫）:移除 rect 內**已 committed** 的舊行（被覆蓋）、把 rect 內**新行標記 committed**。→ 換訊息替換不疊加；PLAY 切頭像（STORE AREA 覆蓋標題區但無新文字）→ 標題被移除。
- **沒有 STORE AREA 的畫面**（地鐵 `emp1.ttm` 0 個）：行維持未 committed、持續顯示（靠 `clearDeferredBg` 在換場景/F8 清）。
- **talking-head 動畫**（`head.cpp` `TalkData::drawAndUpdateVisibleHeads`,**跟 CDS env STORE AREA 不同機制!**）：每幀畫臉後 `clearDeferredBgRect(head._rect)` → 臉蓋住的標題消失（對應英文 header 被臉蓋在底下）。
- `clearDeferredBg()` 在 F8 切語言（cjk.cpp 三個 mode 函式）+ 換場景（dgds.cpp changeScene）呼叫。
- 座標都是 320×200 space；CJK 行高 ≈ `fontHeight()/2 + 1`。

**教訓**：先用 extract_ttm_strings 確認哪些 ttm **有/沒有 STORE AREA** 再決定模型；別假設所有畫面都一樣。

## 4. 對話選項版面

- 選項清單在 zh.json 是一串用 `\r\r` 分隔 → 24px CJK 下每個雙換行多 25px 空行 → **間隔過大 + 超出對話框**。把選項清單條目 `\r\r`→`\r`（純資料,只挑含「1. 2.」編號的 125 條）。
- CJK 選項**高亮反光條**:`drawForeground` CJK 路徑原本在高亮邏輯前就 return。英文 char offset 對不上中文 → 改**用選項編號匹配**（中英文選項都以 `N.` 開頭）重繪該行為 `_selectonFontCol`。多選單溢出時 `zystart` clamp 在框頂。
- **對話框長到容納（文字溢出修正）**:24px CJK 比原英文小字型高,3+ 行對白會超出對話框下緣。`dialog.cpp drawType2` 在繪製前先 `wrapText` 算 CJK 行數 → 把 `_rect.height` **往下長到剛好容納**（`need = lines*lineHeight + 13 + (title?11:0)`,clamp 在 `200 - _rect.y - 1`）。比 `\r\r`→`\r` 收斂更徹底,連 3 長選項都收進框內。HOC 同款(用 `_fileNum?fileNum:sceneNum` 查鍵)。
- **talking-head/視訊臉蓋住名牌**:sprite 每幀覆蓋像素區 → 在 `ttm.cpp` 畫 sprite 後 + `head.cpp` CDS 畫頭後呼叫 `clearDeferredBgRect(sprite rect)`,清掉該區持久 CJK overlay,名牌不浮在臉上。

## 5. 譯名一致性

`CONTEXT.md` 譯名表為準。ROTD 主角 **Blade/William Hunter → 孟波**（City Hunter 盜版梗）,姓 Hunter→獵人或省略,說話人 `BLADE:`→`孟波：`。批次正名要**只改 value 不動英文 key**,規則長/複合在前（威廉·杭特→孟波、杭特先生→孟波先生、威廉→孟波)。其他:阿香(Karyn)、老傑克(The Jake)、鄧黃(Deng Hwang)、強尼阿廣(Jonny Qwong)、文森奇市長(Mayor Vincenzi)、巴哈姆特(Bahumat)、蛇仔(The Snake)、陸(Chen Lu)。

## 6. Android：CI 空殼 + 本地注入（遊戲不上 GitHub）

CI（`.github/workflows/build.yml`）只編**引擎 + 資產**（無遊戲）。本地 `tools/inject_android.sh`（Docker,host 乾淨）把遊戲注入 CI 的 base APK 再重簽。**踩過的雷,缺一不可**:

1. **`liboboe.so not found`**：ScummVM `libscummvm.so` 動態連 `-loboe`,但 CI 只在 build sysroot 連結、沒打包 runtime `.so`。→ 注入 oboe 1.9.0 arm64 `liboboe.so`。
2. **`libc++_shared.so not found`**：預編 oboe 是 c++_shared → 還要 `libc++_shared.so`（從 NDK r26d sysroot 抽,快取 `build/android_libs/`）。configure `7782` 硬連 `-loboe`,**oboe 無法關**(OpenSL ES 已移除)。
3. **`eglCreateWindowSurface() UnsupportedOperationException` → 秒退**（Galaxy S25+/Android 16）：surface race,`patches/android-surface-race.patch` 讓 Java `initSurface()` 等到 surface 有效再建。
4. **遊戲不進 launcher**：ScummVM 只展開 APK **內層** `assets/assets/` 樹（照 `MD5SUMS`）並 mass-add `files/assets/games/*`。→ 遊戲要放 `assets/assets/games/<id>`（**雙層**）+ 把檔案登錄進 `assets/MD5SUMS`（路徑 `assets/games/<id>/<f>`），否則既不展開也不偵測。`android.cpp updateStartSettings` 只在 `assets_updated` 時 mass-add。
5. **直接進遊戲**：`patches/android-autostart-rise.patch` 改 `ScummVMActivity` `intentData==null` → `{"ScummVM","rise"}`（android-job-only,不碰桌面）。
6. **16KB 對齊警告**：`extractNativeLibs=true` 所以只是警告不致命；要全清需三顆 `.so` 都 16KB-aligned（oboe/libc++ 無對齊版 + libscummvm 要 `-z max-page-size=16384`），成本高、低優先。

**adb debug 用 Docker**：`--privileged -v /dev/bus/usb:/dev/bus/usb` + 裝 adb。手機要開 USB 偵錯（會多一個 class 255 / iInterface=ADB 介面才看得到）。`tools/adb_debug.sh` 一條龍：確認 ABI → 重裝 → logcat 抓 crash。

## 7. 全平台 FULL 打包（含遊戲,自留,勿散布）

`scripts/package_full.sh [linux|appimage|windows|mac]`。各平台引擎來源:
- **Linux**：本地 scummvm-src 直接 build。
- **AppImage**：`package_appimage.sh` 重打 `dist/rotd-cht-linux-x86_64`（用更新後 Linux bundle）。
- **Windows**：`build_windows.sh`（Docker mingw 交叉編譯**本地 scummvm-src 工作樹** → 帶最新引擎改動）。exe 預設未 strip 89MB → `x86_64-w64-mingw32-strip` 降 26MB。
- **Mac**：CI `macos-14` runner 出 `.app`（dylibbundler）。`package_full.sh mac` 套 CI `.app` + 遊戲 + `玩-rotd-cht.command`。
- **Android**：CI base APK + `inject_android.sh`。

**改引擎 → 全平台重編**（Mac/Android 走 CI push,Linux/Win/AppImage 本地）。**只改翻譯 → 重建 zh.dtr 部署各包的 zh.dtr**（Linux `share/rotd-cht/`、Win/Mac `extra/`、Android bundle、AppImage 在映像內）。每次部署後 `find dist -name zh.dtr -exec md5sum` 確認全一致。

**安全鐵則**：遊戲/BIOS/disc/`dist/`/`game_en/`/`screenshots/` 全 gitignore,**永不 push**。CI 只產引擎+資產。完整包標「請勿散布」。

### 7b. 改引擎後 dist-all 重打包的編排（D9 實戰）

改引擎要重出**全五包**時,順序很重要 —— Mac/Android 的 binary 是 **CI 從 patch 編的**,本機只有 Linux binary:

1. **先 push patch**（`patches/dgds-cjk.patch` 從 scummvm-src `git diff HEAD -- engines/dgds` 重產）→ 觸發 CI 重編 Mac/Android 的新 binary。**不 push 就沒有含新功能的 Mac/Android binary**;把新模式的資產注入**舊** CI binary 沒用（engine 根本沒載入那條路徑,新 enum 也沒進 `_avail`）。
2. **CI 跑的同時**（~8 分）本機平行做:重打 Linux base bundle → `build_windows.sh`（Docker mingw,本機 binary 已含改動）→ `package_full.sh linux/appimage/windows`。AppImage 繼承 Linux bundle 的 `share/rotd-cht/`,只要先重打 Linux base 就會帶新資產。
3. **CI 完成** → `gh run download <id> -n rotd-cht-android -n rotd-cht-macos -D dist/ci` → `package_full.sh mac`（套 CI `.app`）+ `inject_android.sh`（注入 CI base APK）。
4. **`gh run list` 沒有 `--branch`**,用 `gh run list --limit N`;`gh run view <id>` 看 ARTIFACTS。
- **新語言/資產要同步進每個 asset list**（漏一個那平台就沒新模式）:`package_linux.sh` ASSETS、`build_windows.sh` extra 迴圈、`build_macos.sh` cp、`inject_android.sh` refresh 迴圈、`package_full.sh` mac graft。**CI 不建 de.dtr/ja.dtr**（來源 JSON 是 gitignore 的版權 RE 素材）→ Mac graft + Android refresh 從本機 `build/` 補。
- **`nohup … &` 背景陷阱**:`nohup cmd & echo started` 的 task 會**立刻 exit 0**（那是 launcher 不是 build）。真正的 build detached 在跑 → 別信 launcher 的「completed」,用 `pgrep -f build_windows.sh` + 輸出檔時間戳確認真的跑完。改用 harness 的 `run_in_background`(可被追蹤)更穩。
- **dev+materials tarball**:`tar -I pigz -cf /home/anr2/rotd-cht-DEV+MATERIALS.tar.gz --exclude='…/dist' --exclude='…/segacd_ja/disc.bin' --exclude='…/segacd_ja/rotd_01.iso' -C /home/anr2 rise-of-the-dragon`。放 repo **外**(sibling)保持 dist/ 乾淨 + 避免自己包自己;含整套語音來源/素材/disc → 可在他機重建(語音全進 → 1.4G)。

## 8. Heart of China（HOC）與 ROTD 的差異 ── 換遊戲必看

HOC（Dynamix 1991，gameid `china`，repo `heart-of-china-dos-cht`）是 ROTD 的姊妹作,
**同引擎、同 overlay 機制**,但 SDS/DDS 版本較新（` 1.216` vs ROTD ` 1.211`）→ 幾個關鍵差異:

| 項目 | ROTD | HOC |
|---|---|---|
| 索引檔 | `VOLUME.VGA` | `VOLUME.RMF`（**同格式**,`dgds_volume.py` 直接吃）|
| SDS/DDS 版本 | ` 1.211` | ` 1.216` |
| **對白存放** | inline 在 SDS,key `(scene,num)` | ⭐ **72 個 `D<N>.DDS` 檔**,key `(fileNum,num)` |
| 對白量 | 2,386 | 4,651 |
| UI | `*.req` | `hinv.req` / `hvcr.req` / `hoc.rst` |
| 內建中文字型 | 無 | `chinese.fnt`/`china.fnt`/`hoc.fnt`（劇情有中文場景）|

- **對白不在 SDS,在 DDS**：version ≥1.214 的 `SDSScene::parse` **不呼叫** `readDialogList`;
  對白改由 `Scene::loadDialogData(fileNum)` 從 `D<N>.DDS`（packed `DDS:` chunk:
  magic+ver+id+dialogList）載入,`dst._fileNum = fileNum`。`readDialogList` 對 1.216 的條件分支:
  `isVersionOver(" 1.216")` **恰為 false**（strncmp==0）→ **不讀** `talkDataNum/talkDataHeadNum`。
  抽字工具 = **`tools/extract_dds.py`**（新寫,port 自 scene.cpp,4651 句 0 失敗）。
- **draw hook 的對白鍵要 game-agnostic**：`dialog.cpp drawForeground` 改
  `int dlgKey = _fileNum ? _fileNum : engine->getScene()->getNum();` → HOC 走 DDS fileNum、
  ROTD 走 scene,**同一 binary 兩款通吃**,不必 game-id 分叉。`_str` 仍含 `NAME:\r` 名牌,
  drawType2 拆冒號前當 title 走 `drawHeader`→`lookupUI`（名牌 `UI:CHI`→趙奇）、body 走
  drawForeground→`lookupDialog`,所以**對白譯文存 body-only,名牌另存 `UI:` 鍵**。
- **autopilot `dlg` 要支援 `F:N`**：`autopilot.cpp` 'd' case 解析 `c.name` 的冒號 →
  `showDialog(fileNum, dlgNum)`（fileNum 0 = ROTD 舊行為）,才能強制觸發 HOC DDS 對白做截圖 QA。
- 其餘（CJK 字型、DTRN 打包、F8 setMode、TTM 持久層、三繪字路徑）**完全沿用 ROTD**,
  連 patched scummvm-src 工作樹都可 `cp -a`（HEAD=f4526cf + 未 commit 的 CJK patch + build cache）
  過來,只改 dialog.cpp/autopilot.cpp 兩處 → 增量重編。
- 譯名走**民初冒險通俗派**（1930s 中國環球冒險）:Lucky→老馬、Chi→趙奇、Kate→凱蒂、Li Deng→李鄧。

## 9. Willy Beamish（威利奇遇記）與 HOC/ROTD 的差異 ── 最新版 DGDS

Willy（Dynamix 1992，gameid `beamish`/`GID_WILLY`，repo `the-adventures-of-willy-beamish`）是
DGDS **最新版**（SDS/DDS ` 1.224`）。同 overlay 機制,但版本比 HOC 更新 → 兩個必踩的差異:

| 項目 | HOC | Willy |
|---|---|---|
| 索引檔 | `VOLUME.RMF` | `RESOURCE.MAP`（**同格式**,`dgds_volume.py` 直接吃,3402 資源）|
| 版本 | ` 1.216` | ` 1.224` |
| DDS / 對白 | 72 檔 / 4651 | 68 檔 / **2105**,key `(fileNum,num)` |
| talkie | 無 | ⭐ **CD 配音版**:2158 `.cds` + 62 `.tds`（頭像動畫+語音,**無文字**）|
| UI | `hinv.req`… | `winv.req` / `wvcr.req` + 字型 `willy/comix_16/wvcr.fnt` |

- **版本述詞會反轉**：`readDialogList` 在 ` 1.216` 時 `isVersionOver(" 1.216")`==false（不讀
  talkData）,但 ` 1.224` **為 true → 多讀 `talkDataNum` + `talkDataHeadNum` 兩個 u16**。HOC 的
  抽字器照搬到 Willy 會**錯位**。解法:**動態版本述詞**（從檔案自己的 ver 字串算 over/under,
  鏡射 `strncmp(_version, v, _version.size())`）,一支 `extract_dialogs.py` 通吃所有 DGDS 版本。
- **talkie 字幕仍在 DDS**：CDS/TDS 是頭像+語音,**完全不含可譯字**;字幕文字一直在 DDS `_str`。
  → **翻 DDS = 翻完全部對白字幕**,不必碰 CDS,不必做字幕系統。遊戲內 `Alt+B`/`Alt+T` 開關字幕/語音。
- **名牌做法（與 HOC body-only 不同,更通用）**：Willy 把**完整 `_str`（含「名字：\r」）存進譯文**,
  在 `drawForeground` CJK 路徑**鏡射 drawType2**:僅當 `_frameType==kDlgFrameBorder`（txt!=_str）時剝掉
  開頭「名字：\r」前綴（**Big5-aware**:全形「：」= `0xA1 0x47`,且冒號須緊接 `\r`）。名牌另由
  `tools/gen_ui_names.py` 從 en/zh 平行資料**自動生成 `UI:<英文名>→<中文名>`**（182 條,majority vote）。
  優點:譯者看到的是自然的「威利：…」、名牌與內文譯名保證一致、且**非 type-2 對話**（type-1/3/4,
  名字不切成牌）會保留名字在 body —— HOC 的 body-only 對這些會掉名字。
- **patch 套用**：ROTD `dgds-cjk.patch` 對**現行 ScummVM master**（非只 f4526cf）`git apply` 仍乾淨;
  Willy 專屬只動 `cjk.cpp`（字型檔名 `beamish_*` 依 `GID_WILLY` 泛化）+ `dialog.cpp`（game-agnostic
  key `_fileNum ? _fileNum : scene` + 名牌剝除）+ `autopilot.cpp`（`dlg <file> <num>` 雙數字參數）。
- 譯名走**1990s 兒童冒險喜劇**:主角忠實（Willy→威利）+ 配角玩梗（Nintari→任天哩、戲仿梗考古）。

### 9b. Willy 踩過的新坑（溢出/名牌/LQA/在地化/打包）

- **名牌置中對「矮牌」會切頂 → 要 clamp**：ROTD 的 `request.cpp drawHeader` 名牌置中
  `cjkY = htop + (hheight - cjk.fontHeight())/2` 是為 Dragon 的高牌調的；Beamish 牌框比 24px CJK
  **矮**（`hheight`≈8 < `fontHeight()`=12,320-space），置中算出負 offset → 名字往上推、**頂部被橘框切**。
  解法:`if (cjkY < htop) cjkY = htop;`（矮牌貼齊框頂不切、高牌維持置中,game-agnostic）。換遊戲必查名牌牌框高度。
- **對話框溢出三件套**(已收進 §4):①drawType2 量 CJK 行數自動長高 ②選項 `\r\r`→`\r`(Willy 折 46 條,挑含「N.」編號的) ③`zystart` clamp 框頂。三者並用,24px 三選項才全進框。
- **LQA「ZH16 vs ZH24 文字不一致/亂碼」八成是誤報**：兩種字級**共用同一份 zh.dtr**,文字必然相同,
  差別只在字型大小;16×16 小字易被**看成別字**（唯→咋、法→泓)。**先從 `.dcjk` 抽 glyph 比對**
  （`big5LinearIndex`→offset→印 ASCII 點陣)確認是「正字只是糊」還是「真放錯」,**別憑一張 LQA 截圖就重做字型**。
- **時代雜誌攻略當術語 oracle,但要對遊戲字串校正**：找到《軟體世界》34/35 期攻略(作者阿寬)逐頁轉寫進
  `docs/`,當 1990s 官方術語 oracle。**抓出憑記憶的錯**:寵物青蛙是 **Horny(霍尼,遊戲 40 次)**,不是 Sparky(0 次)。
  但雜誌有 OCR/人工翻譯誤差(Frumpton→Frumford、Nintari→NINTAW),**人名拼字一律以 `dialogs_en.json` 為準**,雜誌只負責還原時代用語。
- **文化在地化可「跨翻譯直接重寫」**：遊戲六個美式電台戲仿(KROK/KMED/KTOK/KBAT/KGOD/KNTY)整組換成 1992 台灣電台
  (中廣青春網/地下電台賣藥/凍蒜伯政論/中華職棒/佈道/台語金曲),改 zh.json value + `UI:<台呼號>→<台名>` 名牌即可(純資料)。中等台味:台語詞點綴勿通篇。
- **全平台打包(Willy 具體值)**：patch base = **ae89011b**(非 ROTD 的 f4526cf);CI(`.github/workflows/build.yml`)
  game id `beamish`、資產 `beamish_zh{16,24}.dcjk`、Android 多套 `android-autostart-beamish.patch`(rise→beamish)。
  Windows 本機 mingw 交叉編譯(可重用 `rotd-emu` image,strip 93M→27M);Android `inject_android.sh` 雙層
  `assets/assets/games/willybeamish` + 補 `liboboe.so`/`libc++_shared.so`(可從 ROTD `build/android_libs/` 直接 cp,arm64 共用)。
- **wine 測 Windows exe 的雷**：`WINEPREFIX` 要在 `$HOME`(不能 `/tmp`,wine 拒絕);`WINEDLLOVERRIDES="mscoree,mshtml="`
  跳過 mono/gecko 安裝對話框;先 `wineboot --init` 等完成再跑;autopilot 的 `saveShot` PNG 在 Windows 會寫 0-byte → 改用 `import` 截 X root。
  **但某些環境 wine prefix 初始化不全(`could not load kernel32.dll, status c0000135`)→ exe 根本跑不起來**;這非 exe 問題,
  別卡在 wine。**fallback = build provenance**:exe 時間戳在改碼之後 + `build_windows.sh` 每次 clean rebuild(刪 .o/configure/make)
  + 同一份 patched source 的 Linux build 已實機驗證 → 即可判定 Windows exe 含該功能(stripped exe 的 `strings` 找不到符號是正常)。

## 10. 片頭標題中文副標 overlay（在英文 logo 下疊中文片名）

需求型態:片頭定格的英文藝術字標題（HOC "HEART OF CHINA" / Willy "Willy Beamish"）下方疊一行
中文片名（中國之心 / 威利奇遇記)。**第四條繪字路徑**,跟 §1 三條無關,獨立做法:

- **Hook 點 = `present2x` 疊在 hi-res 層**(`dgds.cpp` `flushDeferred` 之後),**不是**改遊戲自己的
  片頭繪製碼。`CJKSupport::drawTitleSubtitle(dst)` 在 640×400 CLUT8 buffer 上畫。
- **latch 在標題背景檔名**:`isCJK() && _backgroundFile.hasPrefixIgnoreCase("TITLE")`(HOC 是 `TITLE.SCR`;
  Willy latch `TVNNI/INTROHW/NITTIT` + `_titleTicks` 短閂橋接定格時的 bg 翻頁)。
  ⚠️ **找對 bg 名**:加暫時 `warning("%s", _backgroundFile.c_str())` 跑片頭看序列(DYNAMIX.SCR→**TITLE.SCR**)。
- **⚠️ 別 hook 錯路徑**:HOC `hoc_intro.cpp draw2()` 是**捲動 cinematic**(選「播放片頭」才走、`init()` 載
  `xx.scr`),**不是開機就定格的 attract 標題**。attract 標題是 TTM 畫在 `TITLE.SCR` 上(TTM drawScreen op 才
  setBackgroundFile;HocIntro 直接 drawScreen 不設)。一開始 hook draw2 → debug 顯示 draw2 從沒被呼叫。
- **同一張 bg 內分相 → 像素取樣**:`TITLE.SCR` 先閃遊戲原生毛筆中國之心、再定格英文 logo。只想在英文那相畫:
  **別偵測紅色「HEART OF」**(古地圖銅棕底偏紅會誤判),改**偵測毛筆相獨有的青綠 ink**(低中區 y≈300 取樣,
  `r<110 && g>110 && b>110` 計數 > 閾值 → 是毛筆相 → `return` 不畫)。
- **大字/毛筆字 → 編譯進引擎的 1bpp 遮罩**(別用 24×24 Big5 點陣字,太小又非書法):`tools/build_title_mask.py`
  用毛筆 TTF 把片名渲成 1bpp 遮罩 → 產 `engines/dgds/hoc_title_glyphs.h`(免外部資產、全平台自動帶);
  `drawTitleSubtitle` blit 遮罩:8 向 offset 畫深色描邊 + 金色填,色用 `nearestPalIdx(pal,r,g,b)` 從**當下標題
  調色盤**挑最近 index(金 ~245,208,120;深邊 ~26,30,40)。font-agnostic,換字只重跑工具。
- **⚠️ 繁體毛筆字覆蓋陷阱**:開源行書/草書(ZhiMangXing/LiuJianMaoCao/MaShanZheng)都是**簡體取向 → 只有
  「中之心」缺繁體「國」**(`fontTools getBestCmap` 驗 3/4)。唯 **AR PL UKai(楷書毛筆)** 四字繁體全備。
  傳統字片名用 UKai 楷書毛筆;真・繁體草書開源字幾乎不存在(要更草只能混字或自備)。
- **patch 要含新檔**:`hoc_title_glyphs.h` 是新檔,`git diff HEAD` 不含未追蹤檔 → 先 `git add` 再 `git diff HEAD`
  才會以 new-file 進 patch;`patch -p1 --dry-run` 在 pristine base 驗證乾淨套用。
- **打包雷(換引擎後重打必踩)**:① `package_full.sh do_windows` 只在 exe 不存在才重編 → **刪 `dist/hoc-cht-windows-*`
  快取**強制 mingw 重建,否則包到舊 exe(無新功能)。② Android `inject_android.sh` docker build >400s,**別包
  `timeout 400 ... | tail`**(pipe 把 timeout 退出碼蓋成 0,中途被砍還以為成功)→ 背景無 timeout 跑、等 `SIGNED OK`。

## 11. 第二編碼字型：Big5 + Shift-JIS 共存 = 日文字幕模式（D9）

把日文（或任何非 Big5）字幕接成 **F8 第 N 個顯示模式**。關鍵:**一個引擎、兩套雙位元組編碼**,draw path 依當下字型的 encoding 旗標分派查表。

- **字幕語料來自 whisper 聽寫**:日版 Sega CD 是**真人日配 audio**(非文字),用 `faster-whisper` 聽寫成 `ja.dtr`(DTRN,`lang=3`,Shift-JIS bytes)。**繞過卡關的日文自訂編碼文字 RE**(SD4 是聲音不是文字)。聽寫稿用字有出入但結構/時間軸對得上每句 → 對翻譯也是一手語料。
- **選編碼看覆蓋率**:同一份日文台詞,**Shift-JIS 覆蓋 99.7%**(3/1006 失敗) vs Big5 只 13%。換語言先做覆蓋率測試決定編碼,別預設 Big5。
- **字型** `tools/build_jp_font.py`:Shift-JIS-indexed 24×24,`encoding=1`,從 Noto Sans CJK JP(ttc `index=0`)。SJIS 雙位元組→線性索引:lead `0x81-0x9F`→0-30 / `0xE0-0xFC`→31-59;trail `0x40-0x7E`→0-62 / `0x80-0xFC`→63-188(無 0x7F);`index = leadoff*189 + trailoff`(60×189 = 11340 槽)。
- **引擎改動**(cjk.h/cpp):
  - `BitmapFont` 加 `byte encoding`(0 Big5 / 1 SJIS);`loadFont` 存進去(原本讀掉丟棄那個 byte)。
  - free fn `sjisLinearIndex()`/`isSjisLead()` + member `charIndex(b1,b2)`/`isLeadByte(b)` 依 active font 的 `_enc` 分派;`selectActiveFont()` 設 `_enc = fnt.encoding`。
  - **draw path 三處**(`stringWidth`/`wrapText`/`drawDeferredLine`)把硬寫的 `big5LinearIndex`/`isBig5Lead` 換成 `charIndex`/`isLeadByte` → 同一條路徑中文吃 Big5、日文吃 SJIS。
  - `load()` 多 `loadFont("dragon_ja24.dcjk")` + `loadTranslations("ja.dtr")`,兩者都在才 push `kDispJA` 進 `_avail`;`activeOverlay()` 處理 `kDispJA`→`_ja`。
  - **⚠️ 硬寫 Big5 的地方要 guard**:`drawTitleSubtitle`(城市獵人是硬寫 Big5 索引,畫在 active `_glyphs` 上)在 `_enc != 0`(SJIS 字型 active)時 `return` —— 否則 Big5 索引餵進 SJIS 字型 → 亂碼。
- **驗證(headless autopilot)**:`autopilot.txt` `lang N`(DisplayMode 序:0 EN/Orig,1 ZH24,2 ZH16,3 DE,4 JA)→ `dlg <num>` → `shot <name>`,`scripts/qa_run.sh` 在 Xvfb 跑,Read PNG 看字。**JA→ZH→JA 來回切**驗證 font/overlay 選擇無 regression(切回 ZH 要正確重選 Big5 字型 + zh overlay,名牌也要恢復中文)。
- **README 敘事 payoff**:whisper 聽寫那段(原本只當「日文語料副產品」)→ 現在是**可玩的第五顯示模式**,把「外掛素材」變成「真功能」;showcase 放一張日文實機截圖,voice/segacd 段交叉引用。

## When to apply / NOT

- **Apply**：ROTD 或其他 DGDS 遊戲（Heart of China、Willy Beamish）的 ScummVM 中文化、TTM/對話/名牌英文殘留、TTM 持久層 bug、**片頭標題中文副標 overlay**、**第二編碼字型/日文字幕模式（Big5+SJIS 共存）**、Android 注入打包、全平台 ship。
- **NOT**：非 DGDS 的 ScummVM 引擎（SCUMM 看 `zak-fmtowns-zhtw`）；非 ScummVM 老遊戲（看 `classic-mac-c-game-sdl-port` / `qb64pe-game-linux-port`）。

## Reference
- patch base ScummVM：ROTD `f4526cf`、**Willy `ae89011b`**（換遊戲時 CI `SCUMMVM_COMMIT` 要對齊你 fork 的 base）；`engines/dgds/` 是改動範圍。
- repos：ROTD `Rise-of-the-dragon-cht`、HOC `heart-of-china-dos-cht`、Willy `the-adventures-of-willy-beamish`。
- 工具:`extract_ttm_strings.py`（TTM 抽字）、`dgds_volume.py`（資源抽取,RMF+VGA+MAP 通用）、
  **`extract_dds.py`/`extract_dialogs.py`**（DDS 對白抽字,動態版本述詞通吃 1.216/1.224）、
  `build_translation.py`（zh.dtr）、`build_cjk_font.py`（Big5 點陣字）、`gen_ui_names.py`（en/zh 平行→名牌）、
  `build_windows.sh`（mingw 交叉編譯）、`inject_android.sh`、`adb_debug.sh`。
