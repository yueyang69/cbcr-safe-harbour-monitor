import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './layouts/AppLayout'
import { DashboardPage } from './pages/DashboardPage'
import { DataEntryPage } from './pages/DataEntryPage'
import { SummaryDetailPage } from './pages/SummaryDetailPage'
import { ApprovalPage } from './pages/ApprovalPage'
import { ChatAssistant } from './components/ChatAssistant'
import './styles.css'

export function AppRoutes() { return <Routes><Route element={<AppLayout />}><Route index element={<Navigate to="/dashboard" replace />} /><Route path="dashboard" element={<DashboardPage />} /><Route path="summaries/:id" element={<SummaryDetailPage />} /><Route path="data-entry" element={<DataEntryPage />} /><Route path="approvals" element={<ApprovalPage />} /></Route><Route path="*" element={<Navigate to="/dashboard" replace />} /></Routes> }
export function App() { return <BrowserRouter><AppRoutes /><ChatAssistant /></BrowserRouter> }
