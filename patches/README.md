# patches/

## dgds-cjk.patch

ScummVM `dgds` 引擎的繁中化 patch（engine-side overlay + Big5 點陣字 + 語言切換）。
新增 `engines/dgds/cjk.{h,cpp}`，改 `dialog.cpp` / `request.cpp` / `dgds.{h,cpp}` /
`metaengine.cpp` / `module.mk`。**不改任何遊戲檔。**

### 套用 + build（Linux 開發）

```sh
git clone https://github.com/scummvm/scummvm
cd scummvm
git apply /path/to/Rise-of-the-dragon-cht/patches/dgds-cjk.patch
./configure --disable-all-engines --enable-engine=dgds   # 開發期；release 用完整 build
make -j$(nproc)
```

> 註：patch 取自接近 ScummVM master 的樹（dgds 引擎）。若上游 `dialog.cpp` /
> `request.cpp` 有變動導致 hunk 失敗，依 [`../docs/DESIGN-cjk-engine.md`](../docs/DESIGN-cjk-engine.md)
> 的掛鉤點手動套用。

### 執行期需要的檔案（放在遊戲目錄旁）

- `dragon_zh12.dcjk` — `tools/build_cjk_font.py` 產的 Big5 點陣字。
- `zh.dtr` — `tools/build_translation.py` 把 `translations/zh.json` 打包的譯文。

引擎啟動時自動載入；**F8** 切換 英文 / 中文。

### 重新產生兩個資源

```sh
python3 tools/build_cjk_font.py --size 12 --out dragon_zh12.dcjk
python3 tools/build_translation.py translations/zh.json zh.dtr
```
