/**
 * API client for making requests to backend.
 */

import axios from 'axios'
import type {
  Account,
  AccountCreate,
  AccountUpdate,
  Category,
  CategoryCreate,
  CategoryUpdate,
  ImportUploadResponse,
  ImportConfirmRequest,
  ImportStatusResponse,
  ImportLogResponse,
  TransactionUpdate,
  TransactionListResponse,
  AISettings,
  SettingsResponse,
  DashboardSummary,
  MonthTrend,
  RecentTransaction,
  RecurringGroup,
  DetectionResponse,
} from '@/types'

const API_BASE = `${window.location.protocol}//${window.location.hostname}:8000/api/v1`

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Health check
export const healthCheck = async () => {
  const response = await api.get('/health')
  return response.data
}

// Accounts
export const getAccounts = async () => {
  const response = await api.get<{ items: Account[]; total: number }>('/accounts')
  return response.data
}

export const getAccount = async (id: string) => {
  const response = await api.get<Account>(`/accounts/${id}`)
  return response.data
}

export const createAccount = async (data: AccountCreate) => {
  const response = await api.post<Account>('/accounts', data)
  return response.data
}

export const updateAccount = async (id: string, data: AccountUpdate) => {
  const response = await api.patch<Account>(`/accounts/${id}`, data)
  return response.data
}

export const deleteAccount = async (id: string) => {
  await api.delete(`/accounts/${id}`)
}

// Categories
export const getCategories = async () => {
  const response = await api.get<{ items: Category[]; total: number }>('/categories')
  return response.data
}

export const getCategory = async (id: string) => {
  const response = await api.get<Category>(`/categories/${id}`)
  return response.data
}

export const createCategory = async (data: CategoryCreate) => {
  const response = await api.post<Category>('/categories', data)
  return response.data
}

export const updateCategory = async (id: string, data: CategoryUpdate) => {
  const response = await api.patch<Category>(`/categories/${id}`, data)
  return response.data
}

export const deleteCategory = async (id: string) => {
  await api.delete(`/categories/${id}`)
}

// Imports
export const uploadFile = async (file: File) => {
  const formData = new FormData()
  formData.append('file', file)

  const response = await api.post<ImportUploadResponse>('/imports/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

export const confirmImport = async (
  importId: string,
  data: ImportConfirmRequest
) => {
  const response = await api.post<ImportStatusResponse>(
    `/imports/${importId}/confirm`,
    data
  )
  return response.data
}

export const getImportStatus = async (importId: string) => {
  const response = await api.get<ImportStatusResponse>(
    `/imports/${importId}/status`
  )
  return response.data
}

export const getImportHistory = async () => {
  const response = await api.get<ImportLogResponse[]>('/imports/history')
  return response.data
}

// Transactions
export const getTransactions = async (params: {
  page?: number
  per_page?: number
  account_id?: string
  category_id?: string
  start_date?: string
  end_date?: string
  search?: string
  is_recurring?: boolean
}) => {
  const response = await api.get<TransactionListResponse>('/transactions', {
    params,
  })
  return response.data
}

export const updateTransaction = async (
  id: string,
  data: TransactionUpdate
) => {
  const response = await api.patch(`/transactions/${id}`, data)
  return response.data
}

export const bulkCategorize = async (
  transactionIds: string[],
  categoryId: string
) => {
  const response = await api.post('/transactions/bulk-categorize', {
    transaction_ids: transactionIds,
    category_id: categoryId,
  })
  return response.data
}

export const getDashboardSummary = async (month?: string) => {
  const params = month ? { month } : {}
  const response = await api.get<DashboardSummary>('/dashboard/summary', { params })
  return response.data
}

export const getDashboardTrends = async (months: number = 6) => {
  const response = await api.get<MonthTrend[]>('/dashboard/trends', { params: { months } })
  return response.data
}

export const getRecentTransactions = async (limit: number = 10) => {
  const response = await api.get<RecentTransaction[]>('/dashboard/recent-transactions', { params: { limit } })
  return response.data
}

export const getSettings = async () => {
  const response = await api.get<SettingsResponse>('/settings')
  return response.data
}

export const updateAISettings = async (data: {
  provider?: string
  model?: string
  auto_categorize?: boolean
  clean_merchants?: boolean
  detect_format?: boolean
}) => {
  const response = await api.patch<AISettings>('/settings/ai', data)
  return response.data
}

export const testAIConnection = async () => {
  const response = await api.post<{status: string; response: string}>('/settings/ai/test')
  return response.data
}

// Recurring
export const getRecurringGroups = async (includeInactive: boolean = false) => {
  const response = await api.get<RecurringGroup[]>('/recurring', { params: { include_inactive: includeInactive } })
  return response.data
}

// Alerts
export interface Alert {
  id: string
  type: 'large_purchase' | 'price_increase' | 'new_recurring' | 'unusual_merchant' | 'annual_charge'
  severity: 'info' | 'warning' | 'attention'
  title: string
  description: string
  transaction_id: string | null
  recurring_group_id: string | null
  metadata: Record<string, any> | null
  is_read: boolean
  is_dismissed: boolean
  action_taken: string | null
  created_at: string
}

export interface AlertsListResponse {
  items: Alert[]
  unread_count: number
  total: number
}

export interface AlertSettings {
  id: string
  large_purchase_threshold: number | null
  large_purchase_multiplier: number
  unusual_merchant_threshold: number
  subscription_review_days: number
  annual_charge_warning_days: number
  alerts_enabled: boolean
  created_at: string
  updated_at: string | null
}

export async function getAlerts(params?: {
  is_read?: boolean
  is_dismissed?: boolean
  type?: string
  limit?: number
}) {
  const response = await api.get('/alerts', { params })
  return response.data as AlertsListResponse
}

export async function getUnreadCount() {
  const response = await api.get('/alerts/unread-count')
  return response.data as { count: number }
}

export async function updateAlert(id: string, data: {
  is_read?: boolean
  is_dismissed?: boolean
  action_taken?: string
}) {
  const response = await api.patch(`/alerts/${id}`, data)
  return response.data as Alert
}

export async function markAllAlertsRead() {
  const response = await api.post('/alerts/mark-all-read')
  return response.data
}

export async function deleteAlert(id: string) {
  const response = await api.delete(`/alerts/${id}`)
  return response.data
}

export async function getAlertSettings() {
  const response = await api.get('/alerts/settings')
  return response.data as AlertSettings
}

export async function updateAlertSettings(data: {
  large_purchase_threshold?: number | null
  large_purchase_multiplier?: number
  unusual_merchant_threshold?: number
  alerts_enabled?: boolean
}) {
  const response = await api.patch('/alerts/settings', data)
  return response.data as AlertSettings
}

export const getRecurringGroup = async (id: string) => {
  const response = await api.get<RecurringGroup>(`/recurring/${id}`)
  return response.data
}

export const createRecurringGroup = async (data: {
  name: string
  merchant_pattern: string
  frequency: string
  expected_amount?: number
  category_id?: string
}) => {
  const response = await api.post<RecurringGroup>('/recurring', data)
  return response.data
}

export const updateRecurringGroup = async (id: string, data: {
  name?: string
  merchant_pattern?: string
  frequency?: string
  expected_amount?: number
  is_active?: boolean
}) => {
  const response = await api.patch<RecurringGroup>(`/recurring/${id}`, data)
  return response.data
}

export const deleteRecurringGroup = async (id: string) => {
  await api.delete(`/recurring/${id}`)
}

export const detectRecurring = async () => {
  const response = await api.post<DetectionResponse>('/recurring/detect')
  return response.data
}

export const applyDetection = async (_detectionIndex: number) => {
  const response = await api.post<RecurringGroup>('/recurring/detect/apply', null, {
    params: { detection_index: _detectionIndex } as any
  })
  return response.data
}

export const unmarkTransactionRecurring = async (_transactionId: string) => {
  const response = await api.post('/recurring/transactions/${_transactionId}/unmark')
  return response.data
}

export const markTransactionRecurring = async (_transactionId: string, data: {
  recurring_group_id?: string
  create_new?: boolean
  name?: string
  frequency?: string
}) => {
  await api.post(`/recurring/transactions/${_transactionId}/mark`, data)
}

// Subscription Intelligence

export interface SubscriptionInsight {
  type: 'unused' | 'price_increase' | 'high_cost' | 'annual_upcoming' | 'duplicate'
  recurring_group_id: string
  merchant: string
  amount: number
  frequency: string
  insight: string
  recommendation: string
}

export interface SubscriptionReviewResponse {
  total_monthly_cost: number
  total_yearly_cost: number
  subscription_count: number
  insights: SubscriptionInsight[]
  summary: string
  alert_id?: string
}

export interface UpcomingRenewal {
  recurring_group_id: string
  merchant: string
  amount: number
  frequency: string
  next_date: string
  days_until: number
}

export interface UpcomingRenewalsResponse {
  renewals: UpcomingRenewal[]
  total_upcoming_30_days: number
}

export async function triggerSubscriptionReview() {
  const response = await api.post('/alerts/subscription-review')
  return response.data as SubscriptionReviewResponse
}

export async function getUpcomingRenewals(days: number = 30) {
  const response = await api.get('/alerts/upcoming-renewals', { params: { days } })
  return response.data as UpcomingRenewalsResponse
}

export async function detectAnnualCharges() {
  const response = await api.post('/alerts/detect-annual')
  return response.data
}

export default api


