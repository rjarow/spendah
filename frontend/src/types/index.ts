/**
 * TypeScript types for the application.
 */

export type AccountType = "credit" | "debit" | "bank" | "cash" | "other"

export interface Account {
  id: string
  name: string
  type: AccountType
  learned_format_id: string | null
  is_active: boolean
  created_at: string
}

export interface Category {
  id: string
  name: string
  parent_id: string | null
  color: string | null
  icon: string | null
  is_system: boolean
  created_at: string
  children: Category[]
}

export interface AccountCreate {
  name: string
  type: AccountType
}

export interface AccountUpdate {
  name?: string
  type?: AccountType
  is_active?: boolean
}

export interface CategoryCreate {
  name: string
  parent_id?: string | null
  color?: string | null
  icon?: string | null
}

export interface CategoryUpdate {
  name?: string
  parent_id?: string | null
  color?: string | null
  icon?: string | null
}

export type ImportStatus = "pending" | "processing" | "completed" | "failed"

export interface ColumnMapping {
  date_col: number
  amount_col: number
  description_col: number
  debit_col?: number
  credit_col?: number
  balance_col?: number
}

export interface ImportUploadResponse {
  import_id: string
  filename: string
  row_count: number
  headers: string[]
  preview_rows: string[][]
  detected_format?: DetectedFormat | null
}

export interface AISettings {
  provider: string
  model: string
  auto_categorize: boolean
  clean_merchants: boolean
  detect_format: boolean
}

export interface AvailableProvider {
  id: string
  name: string
  requires_key: boolean
  models: string[]
}

export interface SettingsResponse {
  ai: AISettings
  available_providers: AvailableProvider[]
}

export interface DetectedFormat {
  columns: {
    date: number | null
    amount: number | null
    description: number | null
    category: number | null
    debit: number | null
    credit: number | null
    balance: number | null
  }
  date_format: string
  amount_style: 'signed' | 'separate_columns' | 'parentheses_negative'
  skip_rows: number
  source_guess: string | null
  confidence: number
}

export interface ImportConfirmRequest {
  account_id: string
  column_mapping: ColumnMapping
  date_format: string
  save_format?: boolean
  format_name?: string
}

export interface ImportStatusResponse {
  import_id: string
  status: ImportStatus
  filename: string
  transactions_imported: number
  transactions_skipped: number
  errors: string[]
}

export interface ImportLogResponse {
  id: string
  filename: string
  account_id: string
  status: ImportStatus
  transactions_imported: number
  transactions_skipped: number
  error_message: string | null
  created_at: string
}

export interface Transaction {
  id: string
  hash: string
  date: string
  amount: string
  raw_description: string
  clean_merchant: string | null
  category_id: string | null
  account_id: string
  is_recurring: boolean
  recurring_group_id: string | null
  notes: string | null
  ai_categorized: boolean
  created_at: string
  updated_at: string
}

export interface TransactionUpdate {
  clean_merchant?: string
  category_id?: string
  notes?: string
  is_recurring?: boolean
}

export interface TransactionListResponse {
  items: Transaction[]
  total: number
  page: number
  pages: number
}

export interface CategoryTotal {
  category_id: string
  category_name: string
  amount: number
  percent: number
}

export interface VsLastMonth {
  income_change_pct: number
  expense_change_pct: number
}

export interface DashboardSummary {
  month: string
  total_income: number
  total_expenses: number
  net: number
  by_category: CategoryTotal[]
  vs_last_month: VsLastMonth
}

export interface MonthTrend {
  month: string
  income: number
  expenses: number
  net: number
}

export interface RecentTransaction {
  id: string
  date: string
  merchant: string
  category: string
  amount: number
}

// Recurring types
export type Frequency = 'weekly' | 'biweekly' | 'monthly' | 'quarterly' | 'yearly'

export interface RecurringGroup {
  id: string
  name: string
  merchant_pattern: string
  expected_amount: number | null
  amount_variance: number | null
  frequency: Frequency
  category_id: string | null
  last_seen_date: string | null
  next_expected_date: string | null
  is_active: boolean
  created_at: string
  transaction_count: number | null
}

export interface DetectionResult {
  merchant_pattern: string
  suggested_name: string
  transaction_ids: string[]
  frequency: Frequency
  average_amount: number
  confidence: number
}

export interface DetectionResponse {
  detected: DetectionResult[]
  total_found: number
}

// Alert types
export type AlertType = 'large_purchase' | 'price_increase' | 'new_recurring' | 'unusual_merchant' | 'annual_charge'
export type AlertSeverity = 'info' | 'warning' | 'attention'

export interface Alert {
  id: string
  type: AlertType
  severity: AlertSeverity
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
  alerts_enabled: boolean
  created_at: string
  updated_at: string | null
}
