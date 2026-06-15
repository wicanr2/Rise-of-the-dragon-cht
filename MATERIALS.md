# 素材清單（dev 包內含）

這個 dev+素材包裡的原始材料。**全部受版權，僅供你個人保留、勿散布。**

## 原始遊戲（DOS）
| 檔 | 是什麼 |
|---|---|
| `RiseOfTheDragon.zip` | 原始遊戲（德/英 release） |
| `riseofthedragon-en.zip` | 英文版 |
| `game_en/riseofthedragon/` | 解開的英文版（VOLUME.* + 注入的 CJK 資產）— **CHT 基底** |
| `game/` | 另一份解開的遊戲檔 |

## Sega CD（日版，逆向用）
| 檔 | 是什麼 |
|---|---|
| `Rise of the Dragon - A Blade Hunter Mystery (Japan).chd` | ⭐ **日版 Sega CD disc（壓縮，source）** |
| `Sega Mega CD BIOS.zip` / `Sega CD BIOS.zip` | Mega-CD BIOS（`megacd_j.bin` 等） |
| `segacd_ja/files/` | 解開的日版遊戲檔（1299 個，RE 用） |
| `segacd_ja/frames/`、`rotd_0*.wav`、`cal/` | 解開的影格 / 音軌 / 校正素材 |
| `segacd_ja/ja_raw.json` | ⭐ **日文文字 RE 分析輸出**（自訂編碼，未解；見 `docs/SEGACD_RE_NOTES.md`） |
| `segacd_ja/system/bios_CD_*.bin` | 解開的各區 BIOS |

> **不在包裡（可重生）**：`segacd_ja/disc.bin`（273M）、`segacd_ja/rotd_01.iso`（148M）—— 這是上面 `.chd` 的解開版，用 `tools/segacd_*.sh` / chdman 可從 `.chd` 重建。`dist/`（打包輸出）也不在，重建即生成。

## 怎麼用

- DOS CHT 開發：見 `DEV-SETUP.md`。
- Sega CD 日版逆向：`.chd` + BIOS + `tools/extract_segacd*.py` / `segacd_*.sh`；進度與卡點見 `docs/SEGACD_RE_NOTES.md`（結論：日文是自訂編碼，script-opcode RE 是 blocker）。
