/**
 * TypeScript types for the application.
 */

export type AccountType = "checking" | "savings" | "credit_card" | "investment" | "loan" | "mortgage" | "cash" | "other"

export interface Account {
  id: string
  name: string
  account_type: AccountType
  learned_format_id: string | null
  is_active: boolean
  current_balance: number
  calculated_balance: number | null
  is_stale: boolean
  balance_updated_at: string | null
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
  account_type: AccountType
  starting_balance?: number
}

export interface AccountUpdate {
  name?: string
  account_type?: AccountType
  is_active?: boolean
  current_balance?: number
  balance_updated_at?: string
}

export interface NetWorthSummary {
  total_assets: number
  total_liabilities: number
  net_worth: number
}

export interface AccountWithBalance extends Account {
  current_balance: number
  calculated_balance: number | null
  is_stale: boolean
  is_asset: boolean
  balance_updated_at: string
}

export interface NetWorthBreakdown {
  total_assets: number
  total_liabilities: number
  net_worth: number
  accounts: AccountWithBalance[]
}

export interface NetWorthHistoryPoint {
  date: string
  net_worth: number
  total_assets: number
  total_liabilities: number
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
  account_col?: number
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

export interface APIKeys {
  openrouter_api_key: string | null
  openai_api_key: string | null
  anthropic_api_key: string | null
}

export interface TaskModels {
  categorize: string | null
  merchant_clean: string | null
  format_detect: string | null
  coach: string | null
}

export interface TaskModelsUpdate {
  categorize?: string | null
  merchant_clean?: string | null
  format_detect?: string | null
  coach?: string | null
}

export interface AvailableProvider {
  id: string
  name: string
  requires_key: boolean
  models: string[]
}

export interface SettingsResponse {
  ai: AISettings
  api_keys: APIKeys
  task_models: TaskModels
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
    account: number | null
  }
  date_format: string
  amount_style: 'signed' | 'separate_columns' | 'parentheses_negative'
  skip_rows: number
  source_guess: string | null
  confidence: number
}

export interface ImportConfirmRequest {
  account_id?: string
  column_mapping: ColumnMapping
  date_format: string
  save_format?: boolean
  format_name?: string
  update_balance?: boolean
  new_balance?: number
  auto_create_accounts?: boolean
  default_account_type?: string
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
  date: string
  amount: number
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
  category_id?: string | null
  clean_merchant?: string | null
  notes?: string | null
  is_recurring?: boolean
  recurring_group_id?: string | null
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
export type AlertType = 'large_purchase' | 'price_increase' | 'new_recurring' | 'unusual_merchant' | 'annual_charge' | 'budget_warning' | 'budget_exceeded'
export type AlertSeverity = 'info' | 'warning' | 'attention'

export interface Alert {
  id: string
  type: AlertType
  severity: AlertSeverity
  title: string
  description: string
  transaction_id: string | null
  recurring_group_id: string | null
  budget_id: string | null
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

// Subscription Intelligence types

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

// Privacy types
export interface ProviderPrivacyConfig {
  provider: string
  obfuscation_enabled: boolean
}

export interface TokenStats {
  merchants: number
  accounts: number
  people: number
  date_shift_days: number
}

export interface PrivacySettings {
  obfuscation_enabled: boolean
  provider_settings: ProviderPrivacyConfig[]
  stats: TokenStats
}

export type BudgetPeriod = 'weekly' | 'monthly' | 'yearly'

export interface Budget {
  id: string
  category_id: string | null
  category_name: string | null
  amount: number
  period: BudgetPeriod
  start_date: string
  spent: number
  remaining: number
  percent_used: number
  is_over_budget: boolean
  created_at?: string
  updated_at?: string
}

export interface BudgetProgress {
  id: string
  category_id: string | null
  category_name: string | null
  amount: number
  period: BudgetPeriod
  start_date: string
  spent: number
  remaining: number
  percent_used: number
  is_over_budget: boolean
}

export interface BudgetCreate {
  category_id?: string | null
  amount: number
  period: BudgetPeriod
  start_date: string
}

export interface BudgetUpdate {
  category_id?: string | null
  amount?: number
  period?: BudgetPeriod
  start_date?: string
}

// Coach types
export interface ChatRequest {
  message: string
  conversation_id?: string
}

export interface ChatResponse {
  response: string
  conversation_id: string
  message_id: string
}

export interface CoachMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface ConversationSummary {
  id: string
  title: string | null
  summary: string | null
  last_message_at: string
  message_count: number
  is_archived: boolean
}

export interface ConversationDetail {
  id: string
  title: string | null
  summary: string | null
  started_at: string
  last_message_at: string
  is_archived: boolean
  messages: CoachMessage[]
}

export interface ConversationList {
  items: ConversationSummary[]
  total: number
}

export interface QuickQuestion {
  id: string
  text: string
  category: string
}
