# Research: 照片相簿整理器

## R1. 應用程式形態

- **Decision**: 純前端、本機優先（local-first）的單頁 Web 應用程式（SPA），無後端伺服器。
- **Rationale**: 規格 FR-018 要求資料只存在使用者裝置且不上傳；v1 為單一使用者、無帳號（Assumptions）。
  沒有後端就沒有上傳路徑，隱私需求以架構保證，而非靠規則約束。部署只需靜態檔案。
- **Alternatives considered**:
  - **桌面應用（Tauri / Electron）+ SQLite**：可直接讀寫檔案系統、免複製原始檔；但需打包、簽章、
    跨平台發佈，v1 成本過高。若未來需處理 10 萬張以上照片或免複製原始檔，可再評估。
  - **Next.js 全端 + 伺服器儲存**：與 FR-018「不上傳至外部服務」衝突，否決。

## R2. 語言、框架與建置工具

- **Decision**: TypeScript 6.0.3（`strict: true`）+ React 19.3.1 + Vite 8.3.5（`@vitejs/plugin-react` 6.1.2）。
- **Rationale**: 使用者熟悉 TypeScript / React；React 生態有成熟的無障礙拖放與虛擬捲動套件。
- **Alternatives considered**:
  - **TypeScript 7.0.2（npm latest）**：`typescript-eslint` 8.72.0 的 peer dependency 為
    `typescript >=4.8.4 <6.1.0`，尚不支援 7.x；升到 7.x 會讓型別感知的 lint 無法執行，
    因此先固定 6.0.x，待 `typescript-eslint` 支援後再升級。
  - **Vanilla JS**：bundle 最小，但需自行實作含鍵盤與螢幕閱讀器支援的拖放、虛擬捲動，
    開發與測試成本高且易出錯，否決。
  - **Svelte / Vue**：可行，但使用者主力為 React，否決。

## R3. 路由

- **Decision**: 不引入路由套件；以 hash（`#/`、`#/albums/:dateKey`、`#/albums/:dateKey/photos/:photoId`）
  搭配一個小型 `useHashRoute` hook 管理三種畫面。
- **Rationale**: 僅三個畫面；hash 路由支援瀏覽器上一頁 / 重新整理且可直接部署為靜態檔案。
- **Alternatives considered**: `react-router` 8.5.0 要求 Node `>=22.22.0` 且功能遠超需求，否決。

## R4. 照片匯入方式

- **Decision**: `<input type="file" multiple accept="image/*">`（選檔）與
  `<input type="file" webkitdirectory>`（選資料夾），另支援把檔案拖曳到主頁面匯入。
- **Rationale**: `webkitdirectory` 在 Chrome、Firefox 50+、Safari 11.1+、Safari iOS 18.4+ 皆支援，
  滿足 FR-001「選取多張照片或整個資料夾」。
- **iOS 相容性**：iOS Safari 18.4 才支援 `webkitdirectory`，因此以
  `'webkitdirectory' in document.createElement('input')` 偵測，不支援時隱藏「選擇資料夾」，
  保留 Safari 17+ 的支援範圍（spec.md FR-001 已同步修訂）。
- **Alternatives considered**:
  - `window.showDirectoryPicker()` 僅 Chromium 支援（Firefox、Safari 皆不支援），否決。
  - 把 iOS 最低支援版本提高到 18.4：做法較單純，但會排除 iOS 17 到 18.3 的使用者，否決。

## R5. 儲存

- **Decision**: IndexedDB，透過 Dexie 4.4.7 存取。照片 metadata、相簿、排序設定與二進位資料（原始檔、縮圖）
  分表儲存；匯入時**複製**原始檔到 IndexedDB，不保留對原始檔案的參照。啟動時呼叫
  `navigator.storage.persist()` 降低被瀏覽器清除的風險。
- **Rationale**:
  - 從 `<input>` 取得的 `File` 物件無法跨工作階段保存參照，因此必須複製才能在重新開啟後顯示照片。
  - Blob 存 IndexedDB 在所有主流瀏覽器皆可用；metadata 與 Blob 分表，讓主頁面查詢不必載入大型二進位資料。
  - Dexie 提供 schema 版本遷移、交易與 `liveQuery`，減少手寫 IndexedDB 樣板。
- **Alternatives considered**:
  - **OPFS（Origin Private File System）存 Blob**：大檔效能較佳；但主執行緒的
    `FileSystemFileHandle.createWritable()` 在 Safari 需 26 版，跨瀏覽器寫入需改走 Worker 的
    `createSyncAccessHandle()`，增加複雜度。v1 先用 IndexedDB，若量測顯示大量匯入時寫入成為瓶頸再遷移。
  - **localStorage**：容量約 5 MB 且只能存字串，否決。

## R6. 拍攝日期擷取（EXIF）

- **Decision**: `exifreader` 4.52.0，讀取 `DateTimeOriginal`；缺少時依序 fallback 到 `CreateDate`、
  `File.lastModified`，並記錄 `dateSource`。
- **Rationale**: 持續維護且支援 JPEG、PNG、HEIC 的 metadata；可只讀取檔頭以加速。
- **Alternatives considered**: `exifr` 7.1.3 速度快且廣泛使用，但最後一次發佈為 2021-08，
  長期未發佈的套件難以跟上新格式與安全修補，因此優先選擇仍在維護的套件。

## R7. 日期判定與時區

- **Decision**: EXIF `DateTimeOriginal` 為不含時區的當地時間，直接取其 `YYYY-MM-DD` 作為 `dateKey`，
  **不做時區換算**；fallback 到 `lastModified` 時以裝置當地時區轉換。日期早於 1990-01-01 或晚於
  匯入當下 + 1 天者標記 `dateSuspicious`。
- **Rationale**: 對應規格邊界情況「以照片記錄的當地拍攝時間判定日期，不換算成裝置時區」，
  以及「日期在未來或明顯異常時仍分組但標示」。

## R8. HEIC 支援

- **Decision**: 瀏覽器原生無法解碼時，在 Worker 中動態載入 `heic-to/csp`（`heic-to` 1.6.6 的 CSP 相容版本，
  以 `USE_WASM=0`、`USE_UNSAFE_EVAL=0` 建置的純 JS libheif）將 HEIC 轉為 JPEG 後再產生縮圖；
  原生可解碼時（例如 Safari）直接使用。
- **Rationale**:
  - 動態載入讓解碼器不計入初始 bundle（規格的效能需求：初始 JS ≤ 200 KB gzip）。
  - 預設版本需要放寬 CSP；改用 `heic-to/csp` 可以維持嚴格的 `script-src 'self'`（見 R17）。
  - **授權**：`heic-to` 為 LGPL-3.0。維持獨立的動態載入 chunk、不修改其原始碼，並在
    `THIRD-PARTY-NOTICES.md` 附上授權全文與原始碼位置，讓使用者能替換該函式庫，以符合 LGPL 的要求。
- **Alternatives considered**: `heic2any` 0.0.4 最後發佈為 2023-03，否決。

## R9. 縮圖產生

- **Decision**: 在 Web Worker 中以 `createImageBitmap` + `OffscreenCanvas` 產生最長邊 400px 的 WebP
  縮圖（不支援 WebP 編碼時改用 JPEG），品質 0.8。
- **Rationale**: `OffscreenCanvas`（Safari 16.4+）與 `createImageBitmap`（Safari 15+）跨瀏覽器可用；
  移到 Worker 避免匯入時主執行緒卡頓（INP ≤ 200 毫秒）。400px 足以支援高 DPI 下約 200px 的格子。

## R10. 重複照片偵測

- **Decision**: 以 Web Crypto `crypto.subtle.digest('SHA-256', bytes)` 計算內容雜湊作為 `contentHash`，
  建唯一索引；匯入時雜湊已存在即略過並計入「略過」數量。
- **Rationale**: 精確符合規格「內容完全相同」的定義；SubtleCrypto 全瀏覽器支援，無需額外依賴。
- **Alternatives considered**: 感知雜湊（pHash）可抓「看起來相同」的照片，但超出規格範圍且有誤判，否決。

## R11. 拖放排序

- **Decision**: `@dnd-kit/core` 6.3.1 + `@dnd-kit/sortable` 10.0.0，啟用 Pointer、Touch 與
  Keyboard sensors，使用內建的 screen reader announcements（訊息改為繁體中文）。
- **Rationale**: 內建鍵盤操作與 ARIA live region，直接滿足 FR-009 的鍵盤與螢幕閱讀器操作；
  `DragOverlay` 滿足 FR-008 的放置位置預覽；支援格狀排列。
- **Alternatives considered**:
  - `@dnd-kit/react` 0.5.1：新一代 API，但仍為 1.0 前版本，API 可能變動，否決。
  - 原生 HTML5 Drag and Drop：不支援觸控、無鍵盤操作，需自行補齊無障礙，否決。

## R12. 相簿排序的資料表示

- **Decision**: 單一 `ordering` 紀錄：`mode: 'date' | 'custom'` 與 `customOrder: dateKey[]`。
  - `date` 模式：依 `dateKey` 由新到舊即時排序，忽略 `customOrder`。
  - `custom` 模式：依 `customOrder`；新相簿依日期插入到「第一本日期比它舊的相簿」之前，
    找不到則放最後，不打亂其他相簿的相對順序。
  - 「恢復依日期排序」：`mode` 改回 `date` 並清空 `customOrder`。
- **Rationale**: 個人相簿數量為數百至數千級，整份陣列重寫成本可忽略；比 fractional indexing 簡單。

## R13. 平鋪檢視與虛擬捲動

- **Decision**: `@tanstack/react-virtual` 3.14.22 以「列」為單位虛擬化；欄數由容器寬度計算
  （格子最小 120px、間距 4px，360px 寬度下為 2–3 欄）。縮圖以 `URL.createObjectURL` 顯示並在卸載時 revoke。
- **Rationale**: 滿足 1,000 張以上照片流暢捲動與 SC-003（200 張相簿首屏 1 秒內）。

## R14. 文案與 i18n

- **Decision**: 不引入 i18n 套件；所有文案集中於 `src/i18n/zh-TW.ts`，以型別化的 `t(key, params)` 取用。
- **Rationale**: 文案集中一處便於校對與日後擴充語系；v1 只有一種語系，引入完整 i18n 函式庫屬過早抽象。

## R15. 測試與品質工具

- **Decision**:
  - 單元 / 整合：Vitest 5.0.5 + jsdom 30.1.3 + `@testing-library/react` 16.3.3 +
    `@testing-library/user-event` 14.6.8 + `@testing-library/jest-dom` 7.0.1 + `fake-indexeddb` 6.2.6；
    覆蓋率用 `@vitest/coverage-v8` 5.0.5。
  - 端對端：`@playwright/test` 1.64.1（Chromium、Firefox、WebKit）+ `@axe-core/playwright` 4.14.0 檢查 WCAG。
  - 品質：ESLint 10.13.0 + `typescript-eslint` 8.72.0 + Prettier 3.9.10。
- **Rationale**: 涵蓋單元、整合、端對端三層測試，且三者都能在 CI 自動執行；WebKit 專案確保 Safari 行為（HEIC、Blob）被涵蓋。

## R16. 執行環境

- **Decision**: Node.js 24 LTS（≥ 24.15，目前最新 LTS 為 24.22.1「Krypton」）。
- **Rationale**: jsdom 30.1.3 要求 `^22.22.2 || ^24.15.0 || >=26`；Vitest 5 與 Vite 8 皆相容。
- **目標瀏覽器**：Chrome / Edge 最近 2 版、Firefox 最近 2 版、Safari 17+（macOS / iOS）。

## R17. 內容安全政策（CSP）與「資料不上傳」的驗證

- **Decision**: 正式建置時，由 Vite plugin（`transformIndexHtml`，僅 `apply: 'build'`）在 `index.html`
  注入 CSP meta：`default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:;
  worker-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'`。開發模式不注入，
  因為 Vite 的 HMR 需要 inline script 與 WebSocket。另外以 Playwright 監聽所有請求，斷言沒有任何請求
  送往其他 origin。
- **Rationale**: FR-018 原本只靠「沒有後端」的架構保證；CSP 的 `connect-src 'self'` 讓瀏覽器直接擋下對外
  請求，E2E 測試則負責驗證，兩者都能自動檢查。
- **Alternatives considered**: 以 HTTP header 設定 CSP，效果較完整（可用 `frame-ancestors`），但需依賴部署平台
  的設定；meta 標籤可以跟著靜態檔案走，v1 先用 meta，部署平台確定後再補 header。

## R18. 效能量測與回歸檢查

- **Decision**:
  - 效能量測是**量測腳本**，不是測試：放在 `bench/`，以獨立的 `bench/playwright.bench.config.ts` 執行
    （`npm run bench`），不在 `tests/` 底下，也不屬於 `npm run test` 或 `npm run test:e2e`。
  - 量測項目：初始 JS gzip 大小、500 張匯入耗時、200 張相簿首屏時間、1,000 張捲動的最長任務與平均 FPS，
    以及主頁面與相簿頁面的 LCP、CLS（`PerformanceObserver`）與互動延遲（以 Event Timing API 的最大
    `duration` 作為 INP 的替代指標）。
  - `perf-baseline.json` 記錄上述指標的 baseline。`scripts/check-bundle.mjs` 與 `bench/` 必須同時檢查
    「固定門檻」與「比 baseline 差超過 10%」，任一條件不符即失敗。baseline 只能在 PR 中明確更新並說明理由。
  - baseline 的數值**必須取自 CI**：CI 每次執行都把量測結果上傳成 `bench-results` artifact，建立或更新
    baseline 時從 `main` 分支最近一次成功執行的 artifact 取值，並記錄 runner 規格（`runs-on` 標籤、CPU 型號）。
- **Rationale**:
  - 只檢查固定門檻，無法發現還沒超過門檻、但已經變慢的回歸，因此另加「比 baseline 差超過 10%」的檢查。
  - 測試套件必須具決定性（見 R19）；以實際耗時判斷是否通過的檢查本質上會受機器負載影響，
    所以不能放在測試套件裡，改以量測腳本獨立執行。
  - 本機和 CI 機器的效能差異很大，baseline 取自本機會讓 10% 的比較失去意義。
- **注意**：時間類的指標仍有波動，因此每項量測執行 3 次取中位數再與 baseline 比較。

## R19. 測試的決定性

- **Decision**:
  - 時區固定為 `Asia/Taipei`：`vitest.config.ts` 在檔案最上方設定 `process.env.TZ = 'Asia/Taipei'`（讓 worker
    繼承），`playwright.config.ts` 與 bench 設定檔都使用 `timezoneId: 'Asia/Taipei'`。
  - 檔案修改時間由測試指定：E2E 測試不直接以檔案路徑上傳沒有 EXIF 的照片，而是讀成 Buffer 後以
    `setInputFiles({ name, mimeType, buffer, lastModifiedMs })` 上傳，`lastModifiedMs` 固定為
    `Date.parse('2026-10-07T12:00:00+08:00')`。
  - 需要「現在時間」的函式一律由參數傳入 `now`（例如 `isSuspiciousDate(capturedAt, now)`），測試中傳入固定值。
- **Rationale**: 測試結果不得隨執行順序、真實時間或未固定的亂數種子而改變，否則失敗無法重現。git checkout 不會保留檔案的
  修改時間，若以路徑上傳，Playwright 1.64.1 會帶上 checkout 當下的 `mtimeMs`，使無 EXIF 照片的分組日期每次不同。
- **Alternatives considered**: 在測試前用 `fs.utimes` 修改 fixture 的修改時間，同樣可行，但會改動 repository
  內的檔案狀態；直接指定 `lastModifiedMs` 不會產生副作用，因此採用後者。

## 依賴授權

| 套件 | 授權 | 備註 |
|---|---|---|
| react / react-dom | MIT | |
| dexie | Apache-2.0 | 需保留 NOTICE |
| @dnd-kit/core、@dnd-kit/sortable | MIT | |
| @tanstack/react-virtual | MIT | |
| exifreader | MPL-2.0 | 檔案層級的 copyleft；不修改其原始碼，散佈時附上授權與原始碼位置 |
| heic-to | LGPL-3.0 | 見 R8：獨立 chunk、不修改、附授權與原始碼位置 |

devDependencies 不隨正式建置散佈，不列入 `THIRD-PARTY-NOTICES.md`。

---

## Sources

- https://registry.npmjs.org/ （vite、typescript、react、react-dom、react-router、@vitejs/plugin-react、
  dexie、exifreader、exifr、heic-to、heic2any、@dnd-kit/core、@dnd-kit/sortable、@dnd-kit/react、
  @tanstack/react-virtual、vitest、jsdom、@testing-library/*、fake-indexeddb、@playwright/test、
  @axe-core/playwright、eslint、typescript-eslint、prettier）
- https://nodejs.org/dist/index.json
- https://unpkg.com/@mdn/browser-compat-data/data.json （v8.1.7，2026-10-22）
- https://github.com/clauderic/dnd-kit
- https://github.com/hoppergee/heic-to （`heic-to/csp` 版本）
- https://registry.npmjs.org/playwright-core/1.64.1 （原始碼：`setInputFiles` 以檔案路徑上傳時帶上 `mtimeMs`，
  FilePayload 支援 `lastModifiedMs`）
