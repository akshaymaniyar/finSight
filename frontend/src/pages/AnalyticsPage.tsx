import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  BarChart3,
  TrendingUp,
  Store,
  CreditCard,
  Building2,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  Cell,
  Legend,
} from 'recharts';
import { getCategoryBreakdown, getMonthlyTrend, getTopMerchants } from '../api/analytics';
import type { AnalyticsFilters } from '../api/analytics';
import LoadingSpinner from '../components/LoadingSpinner';
import { formatCurrency, getCategoryColor } from '../utils/formatters';

type TabType = 'credit_card' | 'account';

export default function AnalyticsPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabType>('credit_card');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const cardTypeFilter = activeTab === 'credit_card' ? 'CREDIT_CARD' : 'ACCOUNT';

  const filters: AnalyticsFilters = {
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    card_type: cardTypeFilter,
  };

  const { data: categories, isLoading: catLoading } = useQuery({
    queryKey: ['analytics-categories', activeTab, dateFrom, dateTo],
    queryFn: () => getCategoryBreakdown(filters),
  });

  const { data: trend, isLoading: trendLoading } = useQuery({
    queryKey: ['analytics-trend', activeTab],
    queryFn: () => getMonthlyTrend({ card_type: cardTypeFilter }),
  });

  const { data: merchants, isLoading: merchantLoading } = useQuery({
    queryKey: ['analytics-merchants', activeTab],
    queryFn: () => getTopMerchants({ card_type: cardTypeFilter }),
  });

  const isLoading = catLoading || trendLoading || merchantLoading;

  const handleCategoryClick = (category: string) => {
    const params = new URLSearchParams();
    params.set('category', category);
    if (activeTab === 'credit_card') params.set('card_type', 'credit_card');
    else params.set('card_type', 'account');
    navigate(`/transactions?${params.toString()}`);
  };

  const catData = (categories || []).map((c) => ({
    ...c,
    fill: getCategoryColor(c.category),
  }));

  const trendData = (trend || []).map((t) => ({
    ...t,
    shortMonth: t.month.slice(5),
  }));

  const tabLabel = activeTab === 'credit_card' ? 'Credit Card' : 'Bank Account';

  return (
    <div className="p-4 lg:p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
          <p className="text-sm text-gray-500 mt-1">Deep dive into your spending patterns</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <span className="text-gray-400 text-sm">to</span>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>
      </div>

      {/* CC / Bank Account Tabs */}
      <div className="flex items-center bg-gray-100 rounded-lg p-1 w-fit">
        <button
          onClick={() => setActiveTab('credit_card')}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === 'credit_card'
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <CreditCard size={16} />
          Credit Cards
        </button>
        <button
          onClick={() => setActiveTab('account')}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === 'account'
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <Building2 size={16} />
          Bank Accounts
        </button>
      </div>

      {isLoading ? (
        <LoadingSpinner size={32} text="Loading analytics..." className="py-16" />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Category breakdown */}
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
            <div className="flex items-center gap-2 mb-4">
              <BarChart3 size={18} className="text-indigo-600" />
              <h2 className="text-base font-semibold text-gray-900">{tabLabel} Spending by Category</h2>
            </div>
            {catData.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={catData} layout="vertical" margin={{ left: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                    <XAxis
                      type="number"
                      tick={{ fontSize: 11, fill: '#94a3b8' }}
                      tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
                    />
                    <YAxis
                      dataKey="category"
                      type="category"
                      tick={{ fontSize: 11, fill: '#64748b' }}
                      width={120}
                    />
                    <Tooltip formatter={(value: number) => formatCurrency(value)} />
                    <Bar
                      dataKey="total_amount"
                      radius={[0, 4, 4, 0]}
                      barSize={18}
                      cursor="pointer"
                      onClick={(data) => handleCategoryClick(data.category)}
                    >
                      {catData.map((entry, idx) => (
                        <Cell key={idx} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>

                <div className="mt-4 space-y-2 max-h-48 overflow-y-auto">
                  {catData.map((c) => (
                    <div
                      key={c.category}
                      className="flex items-center justify-between text-sm cursor-pointer hover:bg-gray-50 rounded-lg px-2 py-1 -mx-2 transition-colors"
                      onClick={() => handleCategoryClick(c.category)}
                    >
                      <div className="flex items-center gap-2">
                        <span
                          className="w-2.5 h-2.5 rounded-full"
                          style={{ backgroundColor: c.fill }}
                        />
                        <span className="text-gray-700">{c.category}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-gray-500">{c.percentage.toFixed(1)}%</span>
                        <span className="font-medium text-gray-900">{formatCurrency(c.total_amount)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-sm text-gray-400">
                No category data available
              </div>
            )}
          </div>

          {/* Monthly spending trend */}
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp size={18} className="text-green-600" />
              <h2 className="text-base font-semibold text-gray-900">{tabLabel} Monthly Trend</h2>
            </div>
            {trendData.length > 0 ? (
              <ResponsiveContainer width="100%" height={350}>
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis
                    dataKey="shortMonth"
                    tick={{ fontSize: 11, fill: '#94a3b8' }}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: '#94a3b8' }}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
                  />
                  <Tooltip
                    formatter={(value: number) => formatCurrency(value)}
                    contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0' }}
                  />
                  <Legend />
                  <Line type="monotone" dataKey="total_spent" stroke="#EF4444" name="Expenses" strokeWidth={2} dot={{ r: 3 }} />
                  {activeTab === 'account' && (
                    <Line type="monotone" dataKey="total_income" stroke="#10B981" name="Income" strokeWidth={2} dot={{ r: 3 }} />
                  )}
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[350px] flex items-center justify-center text-sm text-gray-400">
                No trend data available
              </div>
            )}
          </div>

          {/* Top merchants */}
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 lg:col-span-2">
            <div className="flex items-center gap-2 mb-4">
              <Store size={18} className="text-orange-600" />
              <h2 className="text-base font-semibold text-gray-900">Top 20 {tabLabel} Merchants</h2>
            </div>
            {(merchants || []).length > 0 ? (
              <div className="overflow-y-auto max-h-[400px]">
                <table className="w-full">
                  <thead className="sticky top-0 bg-white">
                    <tr className="text-left text-xs font-medium text-gray-500 uppercase">
                      <th className="pb-2 pr-2">#</th>
                      <th className="pb-2">Merchant</th>
                      <th className="pb-2 text-right">Amount</th>
                      <th className="pb-2 text-right">Count</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {(merchants || []).slice(0, 20).map((m, idx) => (
                      <tr key={m.merchant} className="text-sm">
                        <td className="py-2 pr-2 text-gray-400">{idx + 1}</td>
                        <td className="py-2 font-medium text-gray-800 max-w-[300px] whitespace-normal break-words">
                          {m.merchant}
                        </td>
                        <td className="py-2 text-right font-semibold text-gray-900">
                          {formatCurrency(m.total_amount)}
                        </td>
                        <td className="py-2 text-right text-gray-500">{m.transaction_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="h-[200px] flex items-center justify-center text-sm text-gray-400">
                No merchant data available
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
