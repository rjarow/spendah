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
} from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
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

export default api

