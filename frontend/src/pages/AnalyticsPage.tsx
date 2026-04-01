import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart3,
  TrendingUp,
  Store,
  CreditCard,
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
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';
import { getCategoryBreakdown, getMonthlyTrend, getTopMerchants, getCardComparison } from '../api/analytics';
import LoadingSpinner from '../components/LoadingSpinner';
import { formatCurrency, getCategoryColor } from '../utils/formatters';

const DONUT_COLORS = ['#4F46E5', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];

export default function AnalyticsPage() {
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const { data: categories, isLoading: catLoading } = useQuery({
    queryKey: ['analytics-categories', dateFrom, dateTo],
    queryFn: () =>
      getCategoryBreakdown({
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      }),
  });

  const { data: trend, isLoading: trendLoading } = useQuery({
    queryKey: ['analytics-trend'],
    queryFn: getMonthlyTrend,
  });

  const { data: merchants, isLoading: merchantLoading } = useQuery({
    queryKey: ['analytics-merchants'],
    queryFn: getTopMerchants,
  });

  const { data: cardComp, isLoading: cardLoading } = useQuery({
    queryKey: ['analytics-cards'],
    queryFn: getCardComparison,
  });

  const isLoading = catLoading || trendLoading || merchantLoading || cardLoading;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full py-32">
        <LoadingSpinner size={40} text="Loading analytics..." />
      </div>
    );
  }

  const catData = (categories || []).map((c) => ({
    ...c,
    fill: getCategoryColor(c.category),
  }));

  const trendData = (trend || []).map((t) => ({
    ...t,
    shortMonth: t.month.slice(5),
  }));

  const donutData = [
    { name: 'Credit Card', value: cardComp?.credit_card_spend || 0 },
    { name: 'Debit Card', value: cardComp?.debit_spend || 0 },
    { name: 'Account', value: cardComp?.account_spend || 0 },
  ].filter((d) => d.value > 0);

  return (
    <div className="p-4 lg:p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
          <p className="text-sm text-gray-500 mt-1">Deep dive into your spending patterns</p>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="From"
          />
          <span className="text-gray-400 text-sm">to</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="To"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Category breakdown */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 size={18} className="text-indigo-600" />
            <h2 className="text-base font-semibold text-gray-900">Spending by Category</h2>
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
                    width={100}
                  />
                  <Tooltip formatter={(value: number) => formatCurrency(value)} />
                  <Bar dataKey="total_amount" radius={[0, 4, 4, 0]} barSize={18}>
                    {catData.map((entry, idx) => (
                      <Cell key={idx} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>

              <div className="mt-4 space-y-2 max-h-48 overflow-y-auto">
                {catData.map((c) => (
                  <div key={c.category} className="flex items-center justify-between text-sm">
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
            <h2 className="text-base font-semibold text-gray-900">Monthly Spending Trend</h2>
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
                  contentStyle={{
                    borderRadius: '8px',
                    border: '1px solid #e2e8f0',
                  }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="total_spent"
                  stroke="#EF4444"
                  name="Expenses"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
                <Line
                  type="monotone"
                  dataKey="total_income"
                  stroke="#10B981"
                  name="Income"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[350px] flex items-center justify-center text-sm text-gray-400">
              No trend data available
            </div>
          )}
        </div>

        {/* Top merchants */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <div className="flex items-center gap-2 mb-4">
            <Store size={18} className="text-orange-600" />
            <h2 className="text-base font-semibold text-gray-900">Top 20 Merchants</h2>
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
                      <td className="py-2 font-medium text-gray-800 max-w-[180px] truncate">
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
            <div className="h-[300px] flex items-center justify-center text-sm text-gray-400">
              No merchant data available
            </div>
          )}
        </div>

        {/* Card comparison donut */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <div className="flex items-center gap-2 mb-4">
            <CreditCard size={18} className="text-purple-600" />
            <h2 className="text-base font-semibold text-gray-900">Card Comparison</h2>
          </div>
          {donutData.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={donutData}
                    cx="50%"
                    cy="50%"
                    innerRadius={65}
                    outerRadius={100}
                    paddingAngle={4}
                    dataKey="value"
                  >
                    {donutData.map((_, idx) => (
                      <Cell key={idx} fill={DONUT_COLORS[idx % DONUT_COLORS.length]} />
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

              {cardComp?.per_card_breakdown && cardComp.per_card_breakdown.length > 0 && (
                <div className="mt-4 space-y-2">
                  {cardComp.per_card_breakdown.map((card) => (
                    <div
                      key={`${card.bank_name}-${card.card_type}`}
                      className="flex items-center justify-between text-sm"
                    >
                      <span className="text-gray-600">
                        {card.bank_name} - {card.card_type.replace('_', ' ')}
                      </span>
                      <span className="font-medium text-gray-900">
                        {formatCurrency(card.total_amount)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <div className="h-[280px] flex items-center justify-center text-sm text-gray-400">
              No card data available
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
