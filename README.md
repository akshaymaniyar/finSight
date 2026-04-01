# FinSight

A self-hosted personal finance dashboard that automatically parses bank and credit card statement emails from Gmail, extracts transactions from password-protected PDF attachments, and provides analytics, categorization, and AI-powered natural language queries.

Built for Indian banks — supports HDFC, ICICI, Axis, IDFC First, SBI, Kotak, Amex, Yes Bank, IndusInd, PNB, Bank of Baroda, Canara Bank, Federal Bank, and Indian Bank.

---

## Features

### Gmail Integration
- Connects via Google OAuth 2.0 with Gmail readonly access
- Searches for bank statement emails across 50+ known bank sender addresses
- Detects forwarded bank statements by subject pattern (e.g., `Fwd: ICICI Bank Statement...`)
- Downloads and saves PDF attachments to disk for debugging
- Returning users skip the Google consent screen on subsequent logins

### PDF Statement Parsing
- Automatically opens password-protected PDFs using bank-specific password patterns
- Generates multiple password candidates per bank and tries them sequentially
- Supports all major Indian bank password formats:

| Bank | Credit Card Password | Account Password |
|------|---------------------|-----------------|
| HDFC | First 4 letters (UPPER) + last 4 card digits | Customer ID or DOB (DDMMYYYY) |
| ICICI | First 4 letters (lower) + DOB (DDMM) | Same |
| Axis | First 4 letters (UPPER) + DOB (DDMM) | Same |
| IDFC First | DOB (DDMMYYYY) | Same |
| SBI | First 4 letters (UPPER) + DOB (DDMM) | Last 5 mobile digits + DOB (DDMMYY) |
| Kotak | First 4 letters (lower) + DOB (DDMM) | CRN number |
| Amex | First 4 letters (UPPER) + DOB (DDMM) | — |
| Yes Bank | CIF + DOB (DDMMYYYY) | Same |
| IndusInd | First 4 letters (lower) + DOB (DDMM) | First 4 letters (UPPER) + DOB (DDMM) |

### Transaction Extraction
- 21 parsers total: 9 credit card + 12 bank account
- Handles bank-specific PDF formats (HDFC's `DD/MM/YYYY| HH:MM` format, ICICI's `DATE MODE PARTICULARS DEPOSITS WITHDRAWALS BALANCE`, Axis's Dr/Cr suffix format, etc.)
- Multi-line narration handling for bank account statements
- Email body parsing as fallback when PDF is unavailable

### Smart Categorization
- Auto-categorizes transactions into 14 categories: Food & Dining, Shopping, Groceries, Transportation, Bills & Utilities, Entertainment, Health, Education, Rent, EMI, Insurance, Subscriptions, ATM Withdrawal, Salary/Income
- Detects mutual fund investments (Groww, Kuvera, Coin), Zerodha trades, and self-transfers
- Credit card credits are categorized as "Refund/Cashback" or "CC Bill Payment" — never counted as income
- Income is only calculated from bank account credit transactions

### Per-Month Sync & Re-sync
- Month-by-month sync grid showing status, email count, and transaction count
- Re-sync deletes all statements and transactions for a month (CASCADE) and re-fetches everything
- Duplicate prevention via `gmail_message_id` unique constraint and `reference_id` dedup

### Analytics Dashboard
- Income, expenses, investments, and self-transfer summary cards
- Monthly spending trend chart
- Category breakdown pie chart
- Top merchants by spend
- Card comparison (credit card vs debit vs bank account)

### AI Chat (Claude API)
- Natural language queries about your transactions
- Sends actual transaction data (up to 200 rows) to Claude for accurate answers
- Chat history persistence per session

### Profile Management
- Collects first name, last name, DOB, PAN (first 5 chars), mobile (last 5 digits)
- Bank-specific customer IDs for banks that use CRN/CIF as PDF password
- Expandable reference section showing password patterns for each bank
- First-time users are prompted to complete their profile before syncing

---

## Architecture

```
FinSight/
├── backend/                    # Python FastAPI
│   ├── app/
│   │   ├── models/             # SQLAlchemy ORM (User, BankAccount, Statement, Transaction, SyncHistory, ChatHistory)
│   │   ├── routers/            # API endpoints (auth, profile, sync, statements, transactions, analytics, chat)
│   │   ├── schemas/            # Pydantic request/response models
│   │   ├── services/           # Business logic (sync, Gmail, categorization, PDF passwords, chat)
│   │   └── parsers/            # Bank statement parsers
│   │       ├── credit_card/    # 9 CC parsers (HDFC, ICICI, Axis, IDFC, SBI, Kotak, Amex, Yes Bank, IndusInd)
│   │       ├── debit/          # 12 account parsers (HDFC, ICICI, Axis, IDFC, SBI, Kotak, Yes Bank, IndusInd, PNB, BOB, Canara, Indian Bank)
│   │       ├── base.py         # BaseBankParser ABC + ParsedTransaction dataclass
│   │       ├── registry.py     # Parser lookup + forwarded email detection
│   │       ├── pdf_utils.py    # pdfplumber table/text extraction
│   │       ├── pdf_bank_statement.py  # Shared bank account PDF parser
│   │       └── email_utils.py  # HTML cleaning, amount/date/reference extraction
│   ├── saved_attachments/      # Downloaded PDFs organized by month/user (gitignored)
│   ├── requirements.txt
│   └── run.py
├── frontend/                   # React + TypeScript + Vite
│   └── src/
│       ├── pages/              # Login, Dashboard, Sync, Statements, Transactions, Analytics, Chat, Profile
│       ├── api/                # Axios API clients
│       ├── components/         # Sidebar, Layout, StatCard, CategoryBadge, etc.
│       ├── context/            # AuthContext with JWT + OAuth flow
│       └── types/              # TypeScript interfaces
└── .gitignore
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.9+, FastAPI, SQLAlchemy, pdfplumber, httpx |
| Database | MySQL 8.0 |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS v4 |
| Auth | Google OAuth 2.0 (offline access), JWT (PyJWT) |
| AI | Anthropic Claude API (anthropic SDK) |
| Charts | Recharts |

---

## Setup

### Prerequisites

- Python 3.9+
- Node.js 18+
- MySQL 8.0+
- Google Cloud project with Gmail API enabled
- (Optional) Anthropic API key for AI Chat

### 1. Clone and configure

```bash
git clone https://github.com/akshaymaniyar/finSight.git
cd finSight
```

### 2. Backend setup

```bash
cd backend
pip install -r requirements.txt

# Create .env from example
cp .env.example .env
```

Edit `backend/.env` with your credentials:

```env
GMAIL_CLIENT_ID=your-google-client-id
GMAIL_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/callback
ANTHROPIC_API_KEY=sk-ant-...          # Optional, for AI Chat
JWT_SECRET=your-random-secret-key
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your-mysql-password
MYSQL_DATABASE=finsight
FRONTEND_URL=http://localhost:5173
PORT=8000
```

### 3. Create MySQL database

```sql
CREATE DATABASE finsight CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Tables are auto-created on first startup.

### 4. Google OAuth setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable the **Gmail API**
3. Create **OAuth 2.0 credentials** (Web application type)
4. Add authorized redirect URI: `http://localhost:8000/api/auth/callback`
5. Copy Client ID and Client Secret to your `.env`

### 5. Start the backend

```bash
cd backend
python run.py
# Server starts at http://localhost:8000
```

### 6. Frontend setup

```bash
cd frontend
npm install
npm run dev
# Dev server starts at http://localhost:5173
```

### 7. Open the app

Visit `http://localhost:5173` and sign in with Google.

---

## User Flow

1. **Sign in** with Google (first time: grants Gmail read permission; returning: just picks account)
2. **Complete profile** — enter your name and date of birth (used to auto-generate PDF passwords)
3. **Sync months** — select which months to sync from the month grid
4. **View dashboard** — see income, expenses, investments, and category breakdowns
5. **Browse transactions** — filter by bank, category, card type, date range
6. **View statements** — see all parsed email statements with expandable transaction details
7. **Ask AI** — natural language queries like "How much did I spend on food in January?"

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/auth/login` | Generate Google OAuth URL |
| GET | `/api/auth/callback` | OAuth callback (redirects to frontend) |
| GET | `/api/auth/me` | Current user info |
| POST | `/api/auth/demo` | Create/resume demo account |
| GET | `/api/profile` | Get user profile |
| PUT | `/api/profile` | Update user profile |
| GET | `/api/sync/status` | Sync status for last 24 months |
| POST | `/api/sync/month` | Sync a specific month |
| POST | `/api/sync/resync` | Force re-sync (deletes and re-parses) |
| GET | `/api/statements` | List parsed statements |
| GET | `/api/statements/:id` | Statement detail with transactions |
| GET | `/api/transactions` | List transactions with filters |
| GET | `/api/transactions/summary` | Aggregate totals |
| GET | `/api/analytics/by-category` | Category breakdown |
| GET | `/api/analytics/monthly-trend` | Monthly income/expense trend |
| GET | `/api/analytics/top-merchants` | Top merchants by spend |
| GET | `/api/analytics/card-comparison` | Credit vs debit vs account spend |
| POST | `/api/chat` | Send message to AI assistant |
| GET | `/api/chat/history` | Chat history |

---

## Supported Banks

### Credit Card Statements (PDF)
HDFC Bank (Infinia, Diners, Regalia, Swiggy, Tata Neu), ICICI Bank (Amazon Pay, Sapphiro), Axis Bank (Ace, Flipkart, My Zone), IDFC First Bank (Power Plus, Wealth), SBI Card, Kotak Mahindra, American Express, Yes Bank, IndusInd Bank

### Bank Account Statements (PDF)
HDFC Bank, ICICI Bank, State Bank of India, Axis Bank, Kotak Mahindra Bank, IDFC First Bank, Yes Bank, IndusInd Bank, Punjab National Bank, Bank of Baroda, Canara Bank, Indian Bank

### Email Transaction Alerts
All of the above banks — parses individual transaction alert emails (debit/credit notifications)

---

## How PDF Parsing Works

1. **Email fetched** from Gmail with PDF attachment detected
2. **PDF saved** to `backend/saved_attachments/{month}/{user_id}/` for debugging
3. **Password candidates generated** based on user's profile (name, DOB, PAN, customer IDs)
4. **Passwords tried** sequentially until PDF opens
5. **Text extracted** from all pages using pdfplumber
6. **Bank-specific regex** applied to extract date, description, amount, and Cr/Dr indicator
7. **Transactions categorized** and inserted into MySQL with dedup checks

---

## License

MIT
