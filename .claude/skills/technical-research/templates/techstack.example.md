# Tech Stack: 照片相簿整理器

**Source**: [001 research.md](../plans/001-photo-album/research.md)、[002 research.md](../plans/002-album-sharing/research.md)

本檔屬於 Truth：描述系統「現在」使用的執行環境與套件，全專案只有這一份。由 technical-research 依各 plan 的 research.md 直接在本檔新增、修改或刪除，每次異動逐項記在該 plan 的 `truth-delta.md`；版本以 repository 的 `package.json` 與 `package-lock.json` 為準。

## 執行環境

| 項目 | 版本 / 範圍 |
|---|---|
| Node.js | 24 LTS（≥ 24.15） |
| 目標瀏覽器 | Chrome / Edge 最近 2 版、Firefox 最近 2 版、Safari 17+（macOS / iOS） |

## Runtime Dependencies

| 類別 | 套件 | 版本 | 用途 |
|---|---|---|---|
| UI 框架 | react | 19.3.1 | 畫面元件 |
| UI 框架 | react-dom | 19.3.1 | DOM 渲染 |
| 儲存 | dexie | 4.4.7 | IndexedDB 存取 |
| 影像 | exifreader | 4.52.0 | 讀取 EXIF 拍攝日期 |
| 影像 | heic-to（`heic-to/csp`） | 1.6.6 | HEIC 轉 JPEG |
| 互動 | @dnd-kit/core | 6.3.1 | 拖放排序 |
| 互動 | @dnd-kit/sortable | 10.0.0 | 格狀排序 |
| 清單 | @tanstack/react-virtual | 3.14.22 | 虛擬捲動 |

## Dev Dependencies

| 類別 | 套件 | 版本 | 用途 |
|---|---|---|---|
| 語言 | typescript | 6.0.3 | 型別檢查 |
| 建置 | vite | 8.3.5 | 開發伺服器與正式建置 |
| 建置 | @vitejs/plugin-react | 6.1.2 | React 支援 |
| 單元 / 整合測試 | vitest | 5.0.5 | 測試執行器 |
| 單元 / 整合測試 | @vitest/coverage-v8 | 5.0.5 | 覆蓋率 |
| 單元 / 整合測試 | jsdom | 30.1.3 | DOM 模擬環境 |
| 單元 / 整合測試 | @testing-library/react | 16.3.3 | 元件測試 |
| 單元 / 整合測試 | @testing-library/user-event | 14.6.8 | 模擬使用者操作 |
| 單元 / 整合測試 | @testing-library/jest-dom | 7.0.1 | DOM 斷言 |
| 單元 / 整合測試 | fake-indexeddb | 6.2.6 | IndexedDB 模擬 |
| 端對端測試 | @playwright/test | 1.64.1 | E2E 測試與效能量測 |
| 端對端測試 | @axe-core/playwright | 4.14.0 | WCAG 檢查 |
| 品質 | eslint | 10.13.0 | Lint |
| 品質 | typescript-eslint | 8.72.0 | TypeScript lint 規則 |
| 品質 | prettier | 3.9.10 | 格式化 |
