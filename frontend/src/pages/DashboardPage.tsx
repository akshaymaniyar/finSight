import { useQuery } from '@tanstack/react-query';
import {
  TrendingDown,
  TrendingUp,
  Landmark,
  ArrowLeftRight,
} from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';
import { getTransactionSummary } from '../api/transactions';
import { getMonthlyTrend, getCategoryBreakdown } from '../api/analytics';
import { getTransactions } from '../api/transactions';
import StatCard from '../components/StatCard';
import CategoryBadge from '../components/CategoryBadge';
import LoadingSpinner from '../components/LoadingSpinner';
import { formatCurrency, formatDate, getCategoryColor, formatMonth } from '../utils/formatters';

export default function DashboardPage() {
  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['transaction-summary'],
    queryFn: getTransactionSummary,
  });

  const { data: trend, isLoading: trendLoading } = useQuery({
    queryKey: ['monthly-trend'],
    queryFn: getMonthlyTrend,
  });

  const { data: categories, isLoading: catLoading } = useQuery({
    queryKey: ['category-breakdown'],
    queryFn: () => getCategoryBreakdown(),
  });

  const { data: recentTxns, isLoading: txnLoading } = useQuery({
    queryKey: ['recent-transactions'],
    queryFn: () => getTransactions({ limit: 10, offset: 0 }),
  });

  const isLoading = summaryLoading || trendLoading || catLoading || txnLoading;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full py-32">
        <LoadingSpinner size={40} text="Loading dashboard..." />
      </div>
    );
  }

  const trendData = (trend || []).map((t) => ({
    ...t,
    monthLabel: formatMonth(t.month),
    shortMonth: t.month.slice(5),
  }));

  const pieData = (categories || []).slice(0, 8).map((c) => ({
    name: c.category,
    value: c.total_amount,
    color: getCategoryColor(c.category),
  }));

  return (
    <div className="p-4 lg:p-8 max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">Overview of your financial activity</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={TrendingUp}
          label="Total Income"
          value={formatCurrency(summary?.total_income || 0)}
          iconColor="text-green-600"
          iconBg="bg-green-50"
        />
        <StatCard
          icon={TrendingDown}
          label="Total Expenses"
          value={formatCurrency(summary?.total_expenses || 0)}
          iconColor="text-red-600"
          iconBg="bg-red-50"
        />
        <StatCard
          icon={Landmark}
          label="Investments"
          value={formatCurrency(summary?.total_investments || 0)}
          iconColor="text-blue-600"
          iconBg="bg-blue-50"
        />
        <StatCard
          icon={ArrowLeftRight}
          label="Self Transfers"
          value={formatCurrency(summary?.total_self_transfers || 0)}
          iconColor="text-gray-600"
          iconBg="bg-gray-100"
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Monthly trend */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <h2 className="text-base font-semibold text-gray-900 mb-4">Monthly Trend</h2>
          {trendData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis
                  dataKey="shortMonth"
                  tick={{ fontSize: 12, fill: '#94a3b8' }}
                  tickLine={false}
                  axisLine={{ stroke: '#e2e8f0' }}
                />
                <YAxis
                  tick={{ fontSize: 12, fill: '#94a3b8' }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
                />
                <Tooltip
                  formatter={(value: number) => formatCurrency(value)}
                  labelFormatter={(label) => `Month: ${label}`}
                  contentStyle={{
                    borderRadius: '8px',
                    border: '1px solid #e2e8f0',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="total_spent"
                  stroke="#EF4444"
                  name="Expenses"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                />
                <Line
                  type="monotone"
                  dataKey="total_income"
                  stroke="#10B981"
                  name="Income"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-gray-400 text-sm">
              No trend data available
            </div>
          )}
        </div>

        {/* Category pie */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <h2 className="text-base font-semibold text-gray-900 mb-4">By Category</h2>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={90}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {pieData.map((entry, idx) => (
                    <Cell key={idx} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip formatter={(value: number) => formatCurrency(value)} />
                <Legend
                  iconType="circle"
                  iconSize={8}
                  formatter={(value) => (
                    <span className="text-xs text-gray-600">{value}</span>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-gray-400 text-sm">
              No category data available
            </div>
          )}
        </div>
      </div>

      {/* Recent transactions */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
        <div className="px-5 py-4 border-b border-gray-100">
          <h2 className="text-base font-semibold text-gray-900">Recent Transactions</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <th className="px-5 py-3">Date</th>
                <th className="px-5 py-3">Merchant</th>
                <th className="px-5 py-3">Amount</th>
                <th className="px-5 py-3">Category</th>
                <th className="px-5 py-3 hidden md:table-cell">Bank</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {(recentTxns?.transactions || []).map((txn) => (
                <tr key={txn.id} className="hover:bg-gray-50/50 transition-colors">
                  <td className="px-5 py-3 text-sm text-gray-500 whitespace-nowrap">
                    {formatDate(txn.transaction_date)}
                  </td>
                  <td className="px-5 py-3 text-sm font-medium text-gray-900 max-w-[200px] truncate">
                    {txn.merchant}
                  </td>
                  <td className="px-5 py-3 text-sm font-semibold whitespace-nowrap">
                    <span
                      className={txn.transaction_type.toUpperCase() === 'DEBIT' ? 'text-red-600' : 'text-green-600'}
                    >
                      {txn.transaction_type.toUpperCase() === 'DEBIT' ? '-' : '+'}
                      {formatCurrency(Number(txn.amount))}
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    <CategoryBadge category={txn.category} />
                  </td>
                  <td className="px-5 py-3 text-sm text-gray-500 hidden md:table-cell">
                    {txn.bank_name || 'N/A'}
                  </td>
                </tr>
              ))}
              {(!recentTxns?.transactions || recentTxns.transactions.length === 0) && (
                <tr>
                  <td colSpan={5} className="px-5 py-8 text-center text-sm text-gray-400">
                    No transactions yet. Sync your bank statements to get started.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
