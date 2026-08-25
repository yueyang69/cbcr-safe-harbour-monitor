第一阶段目标
# 角色与目标
你是一位资深全栈工程师，同时具备税务数字化产品设计经验。请从零开发一个 Transitional CbCR Safe Harbour 自动化测试与风险预警 MVP。

**技术栈强约束（必须使用）**：
- 后端：Python 3.11+ / FastAPI / SQLAlchemy (异步) / PostgreSQL / Pydantic
- 前端：React 18 / TypeScript / Vite / Tailwind CSS / React Router
- 测试：pytest (后端) + Vitest (前端)
- 开发理念：API-First，前端通过 Axios 调用后端接口。

# 核心产品边界（不可逾越的红线）
- 本系统是 **风险预警工具**，不是 Pillar Two 补足税计算器。
- **绝对禁止**计算 GloBE Top-up Tax。
- 如果某个辖区三项测试全部 FAIL，系统必须停在该处，仅生成风险预警并建议人工进行 GloBE 深度分析。

# 核心业务流程
数据上传（单体公司） -> AI 字段映射（Mock） -> 人工确认映射 -> 数据落库 -> 按辖区汇总 -> Safe Harbour 引擎（确定性规则） -> Dashboard 展示 PASS/FAIL。

# 关键业务规则（请直接硬编码进引擎）
1. **De minimis Test**：当辖区汇总后 `Revenue <= 10,000,000` 且 `PBT <= 1,000,000` 时，直接判定 PASS（豁免）。否则 FAIL。
2. **Simplified ETR Test**：`Simplified ETR = (汇总 Covered Taxes / 汇总 PBT) * 100`。`Applicable_ETR_Threshold` 根据 Fiscal Year 自动匹配：2024=15%，2025=16%，2026=17%。ETR >= 阈值则 PASS。
3. **Routine Profits Test**：`SBIE = (Eligible_Payroll_Costs * 10%) + (Eligible_Tangible_Assets * 8%)`（注：此为简化假设，可在配置中调整）。若 `汇总 PBT <= SBIE` 则 PASS。
- **最终结果**：三项测试中若任意一项 PASS，Final Result 为 PASS；三项全 FAIL，Final Result 为 FAIL。

# 数据库与模块要求（具体实现）
1. **数据模型**：需要建 `companies`（公司表），`financial_data`（原始数据表），`mapping_rules`（AI 映射确认表），`jurisdiction_summary`（辖区汇总结果缓存表，避免每次重算）。
2. **AI 映射**：后端写一个 `/api/mapping/suggest` 接口，函数内**硬编码 Mock 映射字典**（例如：“全年税前利润” -> “CbCR_Profit_Before_Income_Tax”）。前端在数据上传后弹出确认框，User 1 点击确认后调用 `/api/mapping/confirm` 落库。
3. **RBAC 简单实现**：使用 JWT 或 Header 传参 `X-User-Role: subsidiary / hq / reviewer` 区分视图，无需复杂的 OAuth2。

# UI 看板要求（直接生成页面）
为集团总部（User 2）生成一个 Dashboard：
1. **顶部 KPI 卡片**：显示辖区总数、PASS 数量、FAIL 数量、数据不完整数量。
2. **辖区列表表格**：包含 Jurisdiction, Revenue (汇总), PBT (汇总), ETR, SBIE, 三个测试各自的 PASS/FAIL, Final Result。
3. **点击下钻**：点击任意辖区（如 Japan），弹窗或跳转详情页，用自然语言解释该辖区为什么 PASS/FAIL（例如：Japan -> De minimis FAIL (Revenue 15m > 10m), ETR Test PASS (18% > 16%), Routine Profits — (未触发)，所以最终 PASS）。

# 交付执行指令
请从初始化项目开始（提供一键启动脚本 `docker-compose.yml` 或 `start.sh`），直接编写所有核心代码、数据库迁移文件和基本单元测试（至少覆盖 ETR 计算和 De minimis 边界值）。**不要**生成冗长的设计文档，**直接产出可运行的源代码**。

进阶版本目标——引入AI

# 角色与目标
你是一位资深全栈工程师，同时具备税务数字化产品设计经验。我们已完成 MVP 的基础 CRUD 和 Safe Harbour 引擎开发。**当前版本为 V2.0，核心目标是大幅增强 AI 的智能化程度**，让 AI 贯穿数据上传、清洗、诊断、解读全流程，同时**绝对不触碰**核心税务计算（ETR/阈值/SBIE 保持硬编码）。

**技术栈不变**：Python/FastAPI/SQLAlchemy/PostgreSQL 后端 + React/TypeScript/Vite 前端。

# 核心产品边界（严格死守）
- **AI 永不参与 Safe Harbour 核心计算**（`safe_harbour_engine.py` 保持纯确定性逻辑，不改一行）。
- **所有 AI 输出必须经过人工确认才能落库**（数据库层加 `confirmed_by_user` 字段）。
- 当 AI 服务不可用时（API 超时/限流），系统必须**优雅降级**，不阻塞用户手动操作。

# 新增 AI 功能模块（后端 ai_service.py 需实现以下 5 项服务）

## 1. 智能字段映射（升级版）
- **原功能**：硬编码映射（如“全年税前利润” -> “PBT”）。
- **升级点**：调用 LLM API（使用 JSON Mode），当遇到未在硬编码字典中的新字段名时，AI 自动推理并返回 Top 3 候选映射（带置信度）。前端展示下拉选择框，人工点选确认。
- **兜底**：置信度 < 60% 时，强制要求用户从标准字段下拉菜单手动选择。

## 2. 数据异常智能检测（新增）
- **场景**：子公司上传 Excel 后，AI 自动扫描该行所有数值。
- **功能**：检测以下三类异常，前端以⚠️图标+Tooltip展示：
  - **口径异常**：`Covered Taxes / PBT > 100%` 或 `< 0%`（标签：“ETR 异常，请确认是否漏填免税收入或会计差错”）。
  - **波动异常**：对比该公司上一年度同字段数据，若变化超过 ±200%，提示：“[字段名] 较去年变化 300%，请确认业务变动或数据录入错误”。
  - **缺失关键字段**：若 `Eligible_Payroll_Costs` 为空，标红提示：“此字段缺失，将导致 Routine Profits Test 无法计算”。
- **合规**：只预警，不自动修改数值。

## 3. 缺失值智能补全建议（新增）
- **场景**：数据上传时，某个非必填但影响计算的关键字段（如 `Eligible_Tangible_Assets`）为空。
- **功能**：AI 检索该公司历史数据（同一 `company_id` 的往年记录），计算中位数或平均值，给出建议值。例如：“建议填充 Tangible Assets = 5,200,000（基于 2023-2025 年历史均值），点击‘采纳’自动填入，或手动输入。”
- **交互**：前端弹窗，User 1 点击“采纳”或“拒绝”。

## 4. 智能风险简报生成器（新增）
- **场景**：集团总部 Dashboard 顶部。
- **功能**：AI 读取当前所有辖区的 Final Result（PASS/FAIL）及关键指标，生成一段 **不超过 200 字**的中文自然语言摘要，包含：
  - 高风险辖区（FAIL）数量及名单；
  - 每个 FAIL 辖区的核心缺口指标（例如：日本 ETR 14.2% < 16%，缺口 1.8%）；
  - 优先级建议（例如：“建议优先复核日本和荷兰的数据口径”）。
- **展示**：作为一个独立卡片或“AI 简报”按钮，点击后生成。页面显眼位置注明 **“AI 生成摘要，仅供参考，不构成税务意见”**。

## 5. 智能问答助手（税务 Copilot）（新增，可选 MVP）
- **场景**：集团总部用户对某个测试结果不理解时。
- **功能**：页面右下角固定聊天入口（简单输入框+对话气泡），后端调用 LLM，System Prompt 严格限定为：
  > “你是一个税务数据助手，只能回答关于本系统已计算出的 PBT、ETR、SBIE、De minimis 结果等数值的解释。你的回答必须基于系统返回的数据，禁止给出任何补足税计算建议、避税方案或法律意见。如果问题超出范围，统一回复：‘此问题超出我的能力范围，请联系您的税务顾问。’”
- **数据上下文**：每次提问时，后端将当前用户所在辖区的最新汇总数据（JSON）作为 Context 一并传给 LLM。

# 前端交互升级要求
- **数据上传页（User 1）**：增加 AI 检测进度条（“AI 正在扫描数据异常... -> 完成！”），检测完成后自动展示异常列表。
- **总部 Dashboard（User 2）**：
  - 顶部新增“AI 简报”卡片，点击“生成简报”按钮调用接口。
  - 右下角增加“税务助手”浮动按钮，点击弹出聊天窗口。
- **所有 AI 建议**：必须保留“确认/拒绝”按钮，确认后才写入数据库或更新界面状态。

# 后端 API 新增路由
- `POST /api/ai/anomaly-detection`：接收一条财务数据，返回异常列表。
- `POST /api/ai/suggest-missing`：接收字段名和公司 ID，返回建议值。
- `POST /api/ai/briefing`：无参数，读取当前所有辖区汇总数据，返回 AI 简报文本。
- `POST /api/ai/chat`：接收 `{ "message": "xxx", "jurisdiction": "Japan" }`，返回 AI 回复。

# 数据库新增字段
- `financial_data` 表增加：
  - `ai_anomaly_flags` (JSONB)：存储 AI 检测到的异常列表。
  - `missing_suggestion` (JSONB)：存储 AI 对缺失字段的建议值及来源说明。
- `mapping_rules` 表增加：
  - `confidence_score` (Float)：AI 映射置信度。
  - `confirmed_by_user` (Boolean)：人工确认标记。

# 交付执行指令
**基于现有代码进行增量开发**，不要推倒重来。请在现有 `backend/services/ai_service.py` 中实现以上 5 个功能，前端按上述要求新增组件。保留所有原有的确定性计算逻辑不变，所有 AI 调用必须包含超时处理（5 秒）和 Fallback 机制。最后更新单元测试，覆盖新增 AI 服务的 Mock 调用测试。