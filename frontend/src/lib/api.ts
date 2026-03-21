/**
 * API client for making requests to backend.
 */

import axios, { AxiosError } from 'axios'
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
  TaskModels,
  TaskModelsUpdate,
  DashboardSummary,
  MonthTrend,
  RecentTransaction,
  RecurringGroup,
  DetectionResponse,
  PrivacySettings,
  ProviderPrivacyConfig,
  TokenStats,
  NetWorthSummary,
  NetWorthBreakdown,
  NetWorthHistoryPoint,
  Alert,
  AlertsListResponse,
  AlertSettings,
  SubscriptionInsight,
  SubscriptionReviewResponse,
  UpcomingRenewal,
  UpcomingRenewalsResponse,
  Budget,
  BudgetProgress,
  BudgetCreate,
  BudgetUpdate,
  CategorizationRule,
  RuleCreate,
  RuleUpdate,
  RuleListResponse,
  RuleTestRequest,
  RuleTestResponse,
  RuleSuggestion,
  RuleSuggestionsResponse,
} from '@/types'

const API_PORT = import.meta.env.VITE_API_PORT || '8000'
const API_BASE = `${window.location.protocol}//${window.location.hostname}:${API_PORT}/api/v1`

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string }>) => {
    const message = error.response?.data?.detail || error.message || 'An unexpected error occurred'
    console.error('API Error:', message)
    return Promise.reject(new Error(message))
  }
)

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

export const updateAPIKeys = async (data: {
  openrouter_api_key?: string
  openai_api_key?: string
  anthropic_api_key?: string
}) => {
  const response = await api.patch('/settings/api-keys', data)
  return response.data
}

export const fetchProviderModels = async (providerId: string) => {
  const response = await api.get(`/settings/providers/${providerId}/models`)
  return response.data as { models: Array<{ id: string; name: string; label: string }> }
}

export const testAIConnection = async () => {
  const response = await api.post<{status: string; response: string}>('/settings/ai/test')
  return response.data
}

export const updateTaskModels = async (data: TaskModelsUpdate) => {
  const response = await api.patch<TaskModels>('/settings/task-models', data)
  return response.data
}

// Recurring
export const getRecurringGroups = async (includeInactive: boolean = false) => {
  const response = await api.get<RecurringGroup[]>('/recurring', { params: { include_inactive: includeInactive } })
  return response.data
}

// Alerts
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
  const response = await api.post(`/recurring/transactions/${_transactionId}/unmark`)
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

// Budgets
export const getBudgets = async (includeProgress: boolean = false) => {
  const response = await api.get<{ items: Budget[]; total: number }>('/budgets', {
    params: { include_progress: includeProgress },
  })
  return response.data
}

export const getBudget = async (id: string) => {
  const response = await api.get<Budget>(`/budgets/${id}`)
  return response.data
}

export const createBudget = async (data: BudgetCreate) => {
  const response = await api.post<Budget>('/budgets', data)
  return response.data
}

export const updateBudget = async (id: string, data: BudgetUpdate) => {
  const response = await api.patch<Budget>(`/budgets/${id}`, data)
  return response.data
}

export const deleteBudget = async (id: string) => {
  await api.delete(`/budgets/${id}`)
}

export const getBudgetProgress = async (id: string, date?: string) => {
  const url = date
    ? `/budgets/${id}/progress?date=${date}`
    : `/budgets/${id}/progress`
  const response = await api.get<BudgetProgress>(url)
  return response.data
}

export const getNetWorth = async (): Promise<NetWorthSummary> => {
  const response = await api.get<NetWorthSummary>('/networth')
  return response.data
}

export const getNetWorthBreakdown = async (): Promise<NetWorthBreakdown> => {
  const response = await api.get<NetWorthBreakdown>('/networth/breakdown')
  return response.data
}

export const getNetWorthHistory = async (startDate: string, endDate: string): Promise<NetWorthHistoryPoint[]> => {
  const response = await api.get<NetWorthHistoryPoint[]>('/networth/history', {
    params: { start_date: startDate, end_date: endDate }
  })
  return response.data
}

export const updateAccountBalance = async (id: string, balance: number): Promise<Account> => {
  const response = await api.patch<Account>(`/accounts/${id}`, {
    current_balance: balance
  })
  return response.data
}

// Privacy API
export const privacyApi = {
  getSettings: async (): Promise<PrivacySettings> => {
    const response = await api.get<PrivacySettings>('/privacy/settings')
    return response.data
  },

  updateSettings: async (settings: Partial<{
    obfuscation_enabled?: boolean
    provider_settings?: ProviderPrivacyConfig[]
  }>): Promise<PrivacySettings> => {
    const response = await api.patch<PrivacySettings>('/privacy/settings', settings)
    return response.data
  },

  preview: async (text: string): Promise<{ original: string; tokenized: string }> => {
    const response = await api.get<{ original: string; tokenized: string }>('/privacy/preview', { params: { text } })
    return response.data
  },

  getStats: async (): Promise<TokenStats> => {
    const response = await api.get<TokenStats>('/privacy/stats')
    return response.data
  },
}

// Coach API
export const coachApi = {
  chat: async (message: string, conversationId?: string) => {
    const response = await api.post('/coach/chat', {
      message,
      conversation_id: conversationId
    })
    return response.data
  },

  getConversations: async (limit: number = 20, offset: number = 0) => {
    const response = await api.get('/coach/conversations', {
      params: { limit, offset }
    })
    return response.data
  },

  getConversation: async (id: string) => {
    const response = await api.get(`/coach/conversations/${id}`)
    return response.data
  },

  archiveConversation: async (id: string) => {
    const response = await api.post(`/coach/conversations/${id}/archive`)
    return response.data
  },

  deleteConversation: async (id: string) => {
    const response = await api.delete(`/coach/conversations/${id}`)
    return response.data
  },

  getQuickQuestions: async () => {
    const response = await api.get('/coach/quick-questions')
    return response.data
  },
}

// Re-export types for convenience (canonical definitions are in @/types)
export type {
  Alert,
  AlertsListResponse,
  AlertSettings,
  SubscriptionInsight,
  SubscriptionReviewResponse,
  UpcomingRenewal,
  UpcomingRenewalsResponse,
  Budget,
  BudgetProgress,
  BudgetCreate,
  BudgetUpdate,
  CategorizationRule,
  RuleCreate,
  RuleUpdate,
  RuleListResponse,
  RuleTestRequest,
  RuleTestResponse,
  RuleSuggestion,
  RuleSuggestionsResponse,
}

// Rules API
export const getRules = async (isActive?: boolean) => {
  const params = isActive !== undefined ? { is_active: isActive } : {}
  const response = await api.get<RuleListResponse>('/rules', { params })
  return response.data
}

export const getRule = async (id: string) => {
  const response = await api.get<CategorizationRule>(`/rules/${id}`)
  return response.data
}

export const createRule = async (data: RuleCreate) => {
  const response = await api.post<CategorizationRule>('/rules', data)
  return response.data
}

export const updateRule = async (id: string, data: RuleUpdate) => {
  const response = await api.patch<CategorizationRule>(`/rules/${id}`, data)
  return response.data
}

export const deleteRule = async (id: string) => {
  await api.delete(`/rules/${id}`)
}

export const testRule = async (text: string, amount?: number) => {
  const response = await api.post<RuleTestResponse>('/rules/test', { text, amount })
  return response.data
}

export const generateRulesFromCorrections = async (minOccurrences: number = 3) => {
  const response = await api.post<RuleSuggestionsResponse>('/rules/generate-from-corrections', null, {
    params: { min_occurrences: minOccurrences }
  })
  return response.data
}

export const createRuleFromSuggestion = async (suggestionIndex: number) => {
  const response = await api.post<CategorizationRule>('/rules/create-from-suggestion', null, {
    params: { suggestion_index: suggestionIndex }
  })
  return response.data
}

export default api
