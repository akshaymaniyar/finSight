export interface User {
  id: number;
  email: string;
  name: string;
  picture: string | null;
}

export interface AuthResponse {
  authorization_url: string;
}

export interface DemoAuthResponse {
  token: string;
  user: User;
  message: string;
}

export interface MeResponse {
  id: number;
  email: string;
  name: string;
  picture: string | null;
  profile_completed?: boolean;
  has_gmail_access?: boolean;
}

export interface SyncMonth {
  month: string;
  sync_status: 'not_synced' | 'completed' | 'in_progress' | 'failed' | null;
  emails_found: number;
  emails_parsed: number;
  transactions_created: number;
  last_synced: string | null;
}

export interface SyncStatusResponse {
  months: SyncMonth[];
}

export interface SyncResult {
  status: string;
  month: string;
  emails_found: number;
  emails_parsed: number;
  transactions_created: number;
  message: string;
}

export interface SyncHistoryEntry {
  id: number;
  month: string;
  sync_status: string;
  emails_found: number;
  emails_parsed: number;
  transactions_created: number;
  started_at: string;
  completed_at: string | null;
  error_message: string | null;
}

export interface SyncHistoryResponse {
  history: SyncHistoryEntry[];
}

export interface Transaction {
  id: number;
  transaction_date: string;
  merchant: string;
  amount: number | string;
  transaction_type: string;
  category: string;
  sub_category: string | null;
  bank_name: string | null;
  card_type: string;
  raw_description: string | null;
  balance_after: string | null;
  is_self_transfer: boolean;
  is_investment: boolean;
  is_mutual_fund: boolean;
  is_zerodha: boolean;
  is_excluded: boolean;
  value_date: string | null;
  reference_id: string | null;
  statement_id: number | null;
  created_at: string;
}

export interface TransactionsResponse {
  transactions: Transaction[];
  total: number;
  limit: number;
  offset: number;
}

export interface TransactionSummary {
  total_expenses: number;
  total_income: number;
  total_investments: number;
  total_self_transfers: number;
  transaction_count: number;
}

export interface Statement {
  id: number;
  email_id: string;
  email_date: string;
  email_subject: string;
  bank_name: string;
  statement_month: string;
  parse_status: 'pending' | 'parsed' | 'failed' | 'no_transactions';
  transaction_count: number;
  total_amount_due: number | null;
  minimum_amount_due: number | null;
  raw_content: string | null;
  transactions: Transaction[] | null;
  created_at: string;
}

export interface StatementsResponse {
  statements: Statement[];
  total: number;
}

export interface CategoryBreakdown {
  category: string;
  total_amount: number;
  transaction_count: number;
  percentage: number;
}

export interface MonthlyTrend {
  month: string;
  total_spent: number;
  total_income: number;
  transaction_count: number;
}

export interface TopMerchant {
  merchant: string;
  total_amount: number;
  transaction_count: number;
}

export interface CardComparison {
  credit_card_spend: number;
  debit_spend: number;
  account_spend: number;
  per_card_breakdown: {
    card_type: string;
    bank_name: string;
    total_amount: number;
    transaction_count: number;
  }[];
}

export interface ChatMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  session_id: string;
  created_at: string;
}

export interface ChatResponse {
  user_message: string;
  assistant_message: string;
  session_id: string;
}

export interface ChatHistoryResponse {
  messages: ChatMessage[];
  total_count: number;
}
