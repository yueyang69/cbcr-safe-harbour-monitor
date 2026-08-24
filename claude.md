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