# Game Test Report — Rise of the Dragon 繁體中文化

由引擎內建 **autopilot（game-tester）** 自動跑出：照腳本載入場景、切換顯示模式、觸發台詞、
擷取實機畫面，供人工檢查中文排版／斷行／溢出。腳本見 [`tools/game_tester.py`](../tools/game_tester.py)、
報告產生器 [`tools/game_test_report.py`](../tools/game_test_report.py)。

## 測試案例：孟波公寓內心獨白（場景 5）

同一句台詞（英文原文 "20 billion people... we've really screwed up this planet..."）在四種
顯示模式下的實機畫面。一鍵 **F8** 即可循環。

![四模式對照](../screenshots/showcase/qa_modes_contact.png)

| 模式 | 截圖 | 結果 |
|---|---|---|
| 英文（原始） | [qa_s5_en](../screenshots/showcase/qa_s5_en.png) | ✅ 原版英文 |
| 中文 24×24 | [qa_s5_zh24](../screenshots/showcase/qa_s5_zh24.png) | ✅ 五行對話泡泡乾淨斷行、無溢出 |
| 中文 16×16 | [qa_s5_zh16](../screenshots/showcase/qa_s5_zh16.png) | ✅ 同句更貼近原排版、字距緊湊 |
| 德文 | [qa_s5_de](../screenshots/showcase/qa_s5_de.png) | ⚠ 模式快速循環下此格未擷到泡泡（時序/涵蓋；見下） |

## 排版觀察

- **中文 24×24**：對話泡泡自動依字寬斷行，五行完整置中，與原始美術 2× 放大對齊良好。
- **中文 16×16**：同一句更緊湊，適合想貼近原版視覺密度的玩家。
- **德文**：`de.dtr` 以原始 Latin 字型渲染；本次四模式快速循環（每模式 `wait 12`）下未穩定擷到
  該句德文泡泡，屬擷圖時序/該句涵蓋問題，非渲染缺陷（德文模式於選單與其他對話已驗證）。

## 方法與限制

- autopilot 直接驅動引擎（非外部點擊），對白觸發比無頭外部輸入穩定。
- **逐場景熱區掃描**：`GTSTATE` 需 `-d2` 且走正常遊戲主迴圈；目前 autopilot 的 `scene N`
  載入路徑未觸發該迴圈分支，故全場景熱區自動枚舉尚未打通。已用已知 `(scene 5, look 84)`
  作為代表性對白驗證；擴大覆蓋為後續工作（解 autopilot↔主迴圈 GTSTATE 串接）。
