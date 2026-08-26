 CbCR Safe Harbour V2.2 工作流完善任务

## 背景
V2.0已完成AI功能集成，但发现工作流不完整，导致用户无法看到保存的数据在Dashboard显示。
Revenue: 15,000,000
PBT: 1,200,000
Covered Taxes: 200,000
Payroll: 3,000,000
Tangible Assets: 5,000,000
Jurisdiction: Japan
Fiscal Year: 2025
点击 "Save" 后，页面显示 Financial data already exists for company and year，但是我的dashiboard页面好像没有任何显示？
这大概是因为现在很多功能没有集成到前台来，很多地方还有设计缺陷
目前，我认为先完成一个最低的mvp流程
场景1：快速测试
Data Entry保存 → Dashboard自动刷新 → 立即看到结果
（后台自动：审批 + 重建汇总）


## 当前问题

### 问题1：localStorage键名不一致
- `frontend/src/layouts/AppLayout.tsx:9` 保存为 `'cbcr-role'`
- `frontend/src/pages/DataEntryPage.tsx:20` 读取 `'user_role'`
- 导致角色判断失效，isHQ始终为false

### 问题2：缺少Submit工作流
数据保存后无法提交审批，导致流程卡在第一步：
当前流程（不完整）：
Subsidiary保存数据 → ❌ 无Submit按钮 → 无法进入HQ审批

完整流程应该是：
Subsidiary保存数据 → Submit提交 → HQ审批 → Refresh summaries → Dashboard显示

后端API已存在：
- `POST /api/v1/financial-data/{id}/submit` (Subsidiary提交)
- `POST /api/v1/financial-data/{id}/approve` (HQ审批)

但前端完全没有调用这些API的界面。

### 问题3：HQ缺少审批界面
HQ角色登录后，没有：
- 待审批数据列表
- 审批/拒绝按钮
- 已审批数据的状态标识

## 需求清单

### ✅ 任务1：修复localStorage键名
统一使用 `'cbcr-role'`：
- 修改 `DataEntryPage.tsx:20` 从 `'user_role'` 改为 `'cbcr-role'`
- 验证其他地方是否也有类似问题

### ✅ 任务2：Data Entry页面增加Submit功能
**位置**：`frontend/src/pages/DataEntryPage.tsx`

**需求**：
1. 保存成功后，显示已保存数据的卡片/列表
2. 每条数据显示状态徽章：
   - `Draft`（未提交，灰色）
   - `Submitted`（已提交待审批，黄色）
   - `Approved`（已审批，绿色）
3. Draft状态显示"Submit for HQ approval"按钮
4. 点击按钮调用 `POST /financial-data/{id}/submit`
5. 提交后状态更新为Submitted，按钮变为"Waiting for HQ approval"（禁用）

**UI建议**：
```tsx
<div className="saved-data-list">
  <h3>Saved data for this company</h3>
  {savedData.map(item => (
    <div className="data-item">
      <div>
        <strong>{item.jurisdiction}</strong> - FY {item.fiscal_year}
        <StatusBadge status={item.is_approved ? 'Approved' : item.is_submitted ? 'Submitted' : 'Draft'} />
      </div>
      {!item.is_submitted && (
        <button onClick={() => handleSubmit(item.id)}>
          Submit for HQ approval
        </button>
      )}
      {item.is_submitted && !item.is_approved && (
        <span className="status-note">Waiting for HQ approval</span>
      )}
    </div>
  ))}
</div>

API调用：
async function handleSubmit(dataId: string) {
  await submitFinancialData(dataId) // 调用现有的API函数
  // 刷新已保存数据列表
}

✅ 任务3：创建HQ审批页面

新建文件：frontend/src/pages/ApprovalPage.tsx

需求：
1. 显示所有 is_submitted=true && is_approved=false 的数据
2. 按公司和辖区分组展示
3. 显示完整财务数据（revenue, pbt, covered_taxes, payroll, tangible_assets）
4. 每条数据提供"Approve"和"Reject"按钮（MVP阶段先只做Approve）
5. 点击Approve调用 POST /financial-data/{id}/approve
6. 审批后自动从列表移除（或变为已审批状态）
7. 显示"No pending approvals"空状态

UI参考：
<section className="page-wrap">
  <h1>Pending Approvals</h1>
  {pendingData.length === 0 ? (
    <div className="empty-state">
      <strong>No pending approvals</strong>
      <span>All submitted data has been reviewed.</span>
    </div>
  ) : (
    <div className="approval-list">
      {pendingData.map(item => (
        <article className="approval-card">
          <div className="approval-header">
            <h3>{item.company.name}</h3>
            <span>{item.jurisdiction} - FY {item.fiscal_year}</span>
          </div>
          <dl className="approval-data">
            <dt>Revenue</dt><dd>{formatNumber(item.revenue)}</dd>
            <dt>PBT</dt><dd>{formatNumber(item.pbt)}</dd>
            <dt>Covered Taxes</dt><dd>{formatNumber(item.covered_taxes)}</dd>
            <dt>Payroll</dt><dd>{formatNumber(item.payroll)}</dd>
            <dt>Tangible Assets</dt><dd>{formatNumber(item.tangible_assets)}</dd>
          </dl>
          <div className="approval-actions">
            <button className="button button-primary" onClick={() => handleApprove(item.id)}>
              Approve
            </button>
            {/* MVP阶段暂不实现Reject */}
          </div>
        </article>
      ))}
    </div>
  )}
</section>

API集成：
// frontend/src/api/endpoints.ts 新增
export async function approveFinancialData(id: string): Promise<FinancialData> {
  const { data } = await api.post<FinancialData>(`/financial-data/${id}/approve`)
  return data
}

// 获取待审批数据（已有listFinancialData，需过滤）
const allData = await listFinancialData()
const pending = allData.filter(d => d.is_submitted && !d.is_approved)

✅ 任务4：路由和导航集成

修改：frontend/src/App.tsx

添加路由：
<Route path="approvals" element={<ApprovalPage />} />

修改：frontend/src/layouts/AppLayout.tsx

添加导航链接（仅HQ角色可见）：
<nav className="nav-list">
  <NavLink to="/dashboard">Dashboard</NavLink>
  <NavLink to="/data-entry">Data entry</NavLink>
  {role === 'hq' && (
    <NavLink to="/approvals">
      <span aria-hidden="true">✓</span>Approvals
    </NavLink>
  )}
</nav>

✅ 任务5：CSS样式补充

修改：frontend/src/styles.css

添加新样式：
/* Saved data list in Data Entry */
.saved-data-list { margin-top: 24px; padding: 20px; background: #f8fafb; border-radius: 6px; }
.data-item { display: flex; align-items: center; justify-content: space-between; padding: 12px; background: #fff; border: 1px solid #e0e7ee; border-radius: 4px; margin-bottom: 8px; }
.status-note { color: #66758b; font-size: 12px; font-style: italic; }

/* Approval page */
.approval-list { display: grid; gap: 16px; margin-top: 24px; }
.approval-card { background: #fff; border: 1px solid #e0e7ee; border-radius: 8px; padding: 24px; }
.approval-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid #e8edf1; }
.approval-header h3 { margin: 0; font-size: 18px; }
.approval-data { display: grid; grid-template-columns: auto 1fr; gap: 8px 16px; margin-bottom: 20px; }
.approval-data dt { color: #66758b; font-size: 12px; font-weight: 600; }
.approval-data dd { margin: 0; color: #172033; font-size: 14px; font-weight: 600; }
.approval-actions { display: flex; gap: 12px; justify-content: flex-end; }

验证清单

完成后验证以下场景：

场景1：Subsidiary完整流程

1. 切换到Subsidiary角色
2. Data Entry页面保存Japan数据
3. 验证下方显示已保存数据卡片，状态为"Draft"
4. 点击"Submit for HQ approval"按钮
5. 验证状态变为"Submitted"，按钮变为禁用的"Waiting for HQ approval"

场景2：HQ审批流程

1. 切换到HQ角色
2. 点击左侧导航"Approvals"
3. 验证看到刚才提交的Japan数据
4. 查看数据详情（revenue, pbt等）
5. 点击"Approve"按钮
6. 验证数据从列表消失（或状态变为已审批）

场景3：Dashboard显示

1. 保持HQ角色
2. 前往Dashboard页面
3. 点击"↻ Refresh summaries"按钮
4. 验证Japan辖区出现在表格中
5. 验证Safe Harbour测试结果正确显示

场景4：角色隔离

1. 切换到Reviewer角色
2. 验证左侧导航没有"Approvals"链接
3. 验证无法访问 /approvals 路由（如果尝试直接访问，应显示权限错误或重定向）

实现注意事项

1. 权限控制：前端UI只是辅助，后端API已有权限验证，前端主要是提升UX
2. 状态同步：Submit/Approve操作后，需要重新获取数据列表以更新UI
3. 错误处理：API调用失败时显示友好错误提示
4. 加载状态：Submit/Approve按钮点击后显示loading状态，防止重复点击
5. 数据刷新：审批后建议显示Toast提示："Data approved successfully. Go to Dashboard and click 'Refresh summaries' to see results."

不要改动的部分

- ❌ 不要修改 Safe Harbour 核心计算逻辑（safe_harbour.py）
- ❌ 不要修改 AI 服务功能
- ❌ 不要修改数据库schema（已有字段足够）
- ❌ 不要改变现有API端点的行为

期望输出

完成后应该有：
1. 修复后的 DataEntryPage.tsx（含Submit按钮和已保存数据列表）
2. 新建的 ApprovalPage.tsx（HQ审批界面）
3. 更新的 App.tsx（新路由）
4. 更新的 AppLayout.tsx（Approvals导航链接 + localStorage修复）
5. 更新的 endpoints.ts（新增approveFinancialData函数）
6. 更新的 styles.css（新增样式）
7. 更新的 V2.0_DELIVERY_SUMMARY.md（记录V2.2改动）

开始实现吧！
