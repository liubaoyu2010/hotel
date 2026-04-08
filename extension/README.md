# Chrome Extension (MVP)

当前已实现最小可用 MVP（Manifest V3）：

- 登录获取 JWT（`/api/v1/auth/login`）
- 扩展绑定（`/api/v1/extension/register`）
- 手动上报测试数据（`/api/v1/extension/report`）
- content-script 自动采集（美团页面注入后自动尝试提取并上报）
- 上报失败重试队列（后台每分钟自动重试，支持手动触发）
- 采集开关与最小采集间隔配置（默认开启，默认120秒）
- popup 显示最近一次自动采集结果
- 自动采集指纹去重（同一批数据在去重窗口内不重复上报）
- 竞品别名映射（rawName -> backendName）
- 最近10条自动上报历史
- Alias Map 与后端 `competitor-aliases` API 双向同步
- 支持“未匹配竞品 -> 一键映射到选中标准竞品”
- 支持“自动建议映射”（基于名称相似度）
- 支持建议项逐条勾选确认（含相似度分值）
- 建议自动勾选阈值可配置（默认 `0.45`）
- 最近10条映射变更历史（alias from -> to）
- 支持按历史逐条回滚映射变更
- 支持一键撤销最近1条映射变更
- 支持清空映射变更历史
- 支持导出/导入 Alias Snapshot（包含 alias map、history、threshold）
- 导入支持模式选择（全量 / 仅 map / 仅 history）
- `Map Only` 支持导入策略（Replace All / Merge Into Existing）
- 导入确认会显示 map 变更预览（新增/更新/删除）
- 导入 map 后自动执行校验（目标 canonical 是否存在于竞品库，含抽样结果）
- 本地持久化 `apiBase`、`jwtToken`、`extensionToken`、`deviceId`

## 文件结构

- `manifest.json`
- `background/service-worker.js`
- `popup/popup.html`
- `popup/popup.js`

## 本地加载步骤

1. 打开 Chrome -> 扩展程序 -> 开启开发者模式
2. 选择“加载已解压的扩展程序”
3. 目录选择当前 `extension/`

## 测试流程

1. Popup 里选 API 地址（推荐 `http://127.0.0.1:8001`）
2. 点击 `1) Login`
3. 点击 `2) Bind Extension`
4. 点击 `3) Report Test Data`
5. 预期返回 `processed_count >= 1`
6. 打开任意 `e.meituan.com` 或 `kd.meituan.com` 页面，等待自动采集上报
7. 如网络异常可查看 `Queue Status` 并使用 `Retry Queue`
8. 可通过 `Auto Collect Enabled` 和 `Min Collect Interval` 调整采集策略
9. 可在 `Alias Map` 设置竞品别名映射，例如 `{"smoke competitor":"Smoke Competitor"}`
10. 若出现未匹配，可在 `Unmatched Competitors` 中查看并使用一键映射
11. 点击 `Suggest Mapping` 生成建议后，可用 `Apply Suggested Mapping` 一键应用
12. 可按相似度分值与勾选状态筛选后再应用，降低误映射风险
13. 可配置建议自动勾选阈值（`Suggestion Auto-Select Threshold`）
14. 低分建议（低于阈值）默认不勾选并高亮，应用前会弹出确认摘要
15. 每次保存映射后可在 `Alias Change History` 查看最近变更
16. 可点击历史中的 `Rollback` 按钮，按条恢复映射
17. 可点击 `Undo Latest` 快速撤销最近1条映射
18. 可点击 `Clear History` 清空历史（不改当前 Alias Map）
19. 可点击 `Export Snapshot` 导出并复制当前 Alias 快照 JSON
20. 将快照 JSON 粘贴到文本框，选择 `Import Mode` 后点击 `Import Snapshot`
21. `Map Only` 下可选择 `Map Import Strategy`：全量替换或合并导入

## 下一步

- 增加 content-script 页面采集（美团后台 DOM）
- 增加失败重试队列
- 增加采集开关与状态面板
