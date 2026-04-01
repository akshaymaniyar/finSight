import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FileText, ChevronDown, ChevronUp, Eye, X } from 'lucide-react';
import { getStatements, getStatement } from '../api/statements';
import type { Statement } from '../types';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';
import CategoryBadge from '../components/CategoryBadge';
import { formatDate, formatCurrency, truncate, getStatusColor } from '../utils/formatters';

export default function StatementsPage() {
  const [bankFilter, setBankFilter] = useState('');
  const [monthFilter, setMonthFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [rawModalId, setRawModalId] = useState<number | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['statements', bankFilter, monthFilter, statusFilter],
    queryFn: () =>
      getStatements({
        bank_name: bankFilter || undefined,
        month: monthFilter || undefined,
        parse_status: statusFilter || undefined,
        limit: 100,
      }),
  });

  const { data: expandedStatement } = useQuery({
    queryKey: ['statement-detail', expandedId],
    queryFn: () => getStatement(expandedId!),
    enabled: expandedId !== null,
  });

  const { data: rawStatement } = useQuery({
    queryKey: ['statement-raw', rawModalId],
    queryFn: () => getStatement(rawModalId!),
    enabled: rawModalId !== null,
  });

  const statements = data?.statements || [];

  // Extract unique banks and months for filters
  // Filter out null bank names and PDF-source entries (they're merged with parent)
  const banks = [...new Set(statements.map((s) => s.bank_name).filter(Boolean))].sort();
  // statement_month comes as "2026-01-01" — convert to "2026-01" for the API
  const months = [...new Set(
    statements.map((s) => s.statement_month?.slice(0, 7)).filter(Boolean)
  )].sort().reverse();

  const toggleExpand = (id: number) => {
    setExpandedId(expandedId === id ? null : id);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full py-32">
        <LoadingSpinner size={40} text="Loading statements..." />
      </div>
    );
  }

  return (
    <div className="p-4 lg:p-8 max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Bank Statements</h1>
        <p className="text-sm text-gray-500 mt-1">Parsed email statements and their transactions</p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={bankFilter}
          onChange={(e) => setBankFilter(e.target.value)}
          className="px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
        >
          <option value="">All Banks</option>
          {banks.map((b) => (
            <option key={b} value={b}>
              {b}
            </option>
          ))}
        </select>
        <select
          value={monthFilter}
          onChange={(e) => setMonthFilter(e.target.value)}
          className="px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
        >
          <option value="">All Months</option>
          {months.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
        >
          <option value="">All Statuses</option>
          <option value="parsed">Parsed</option>
          <option value="pending">Pending</option>
          <option value="failed">Failed</option>
          <option value="no_transactions">No Transactions</option>
        </select>
      </div>

      {/* Table */}
      {statements.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No statements found"
          description="Sync your bank statement emails to see them here."
        />
      ) : (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-50/50">
                  <th className="px-5 py-3 w-8" />
                  <th className="px-5 py-3">Date</th>
                  <th className="px-5 py-3">Bank</th>
                  <th className="px-5 py-3">Subject</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Transactions</th>
                  <th className="px-5 py-3 w-10" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {statements.map((stmt: Statement) => (
                  <StatementRow
                    key={stmt.id}
                    statement={stmt}
                    isExpanded={expandedId === stmt.id}
                    onToggle={() => toggleExpand(stmt.id)}
                    onViewRaw={() => setRawModalId(stmt.id)}
                    expandedData={expandedId === stmt.id ? expandedStatement : undefined}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Raw content modal */}
      {rawModalId !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-3xl w-full max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <h3 className="text-base font-semibold text-gray-900">Raw Email Content</h3>
              <button
                onClick={() => setRawModalId(null)}
                className="p-1.5 rounded-md hover:bg-gray-100 transition-colors"
              >
                <X size={18} />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6">
              {rawStatement?.raw_content ? (
                <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono leading-relaxed">
                  {rawStatement.raw_content}
                </pre>
              ) : (
                <p className="text-sm text-gray-400">No raw content available</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatementRow({
  statement,
  isExpanded,
  onToggle,
  onViewRaw,
  expandedData,
}: {
  statement: Statement;
  isExpanded: boolean;
  onToggle: () => void;
  onViewRaw: () => void;
  expandedData?: Statement;
}) {
  return (
    <>
      <tr
        onClick={onToggle}
        className="hover:bg-gray-50/50 transition-colors cursor-pointer"
      >
        <td className="px-5 py-3">
          {isExpanded ? (
            <ChevronUp size={16} className="text-gray-400" />
          ) : (
            <ChevronDown size={16} className="text-gray-400" />
          )}
        </td>
        <td className="px-5 py-3 text-sm text-gray-500 whitespace-nowrap">
          {formatDate(statement.email_date)}
        </td>
        <td className="px-5 py-3 text-sm font-medium text-gray-900">{statement.bank_name}</td>
        <td className="px-5 py-3 text-sm text-gray-600">
          <div className="whitespace-normal break-words max-w-md">
            {statement.email_subject}
          </div>
        </td>
        <td className="px-5 py-3">
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(
              statement.parse_status
            )}`}
          >
            {statement.parse_status}
          </span>
        </td>
        <td className="px-5 py-3 text-sm text-gray-500">{statement.transaction_count}</td>
        <td className="px-5 py-3">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onViewRaw();
            }}
            className="p-1.5 rounded-md hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
            title="View raw content"
          >
            <Eye size={16} />
          </button>
        </td>
      </tr>
      {isExpanded && expandedData?.transactions && expandedData.transactions.length > 0 && (
        <tr>
          <td colSpan={7} className="px-5 py-3 bg-gray-50/50">
            <div className="rounded-lg border border-gray-200 overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="text-left text-xs font-medium text-gray-500 bg-gray-100/50">
                    <th className="px-4 py-2">Date</th>
                    <th className="px-4 py-2">Merchant</th>
                    <th className="px-4 py-2">Amount</th>
                    <th className="px-4 py-2">Category</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-white">
                  {expandedData.transactions.map((txn) => (
                    <tr key={txn.id}>
                      <td className="px-4 py-2 text-xs text-gray-500">{formatDate(txn.transaction_date)}</td>
                      <td className="px-4 py-2 text-xs font-medium text-gray-800">{txn.merchant}</td>
                      <td className="px-4 py-2 text-xs font-semibold">
                        <span
                          className={
                            txn.transaction_type.toUpperCase() === 'DEBIT' ? 'text-red-600' : 'text-green-600'
                          }
                        >
                          {txn.transaction_type.toUpperCase() === 'DEBIT' ? '-' : '+'}
                          {formatCurrency(Number(txn.amount))}
                        </span>
                      </td>
                      <td className="px-4 py-2">
                        <CategoryBadge category={txn.category} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </td>
        </tr>
      )}
      {isExpanded && expandedData?.transactions && expandedData.transactions.length === 0 && (
        <tr>
          <td colSpan={7} className="px-5 py-6 bg-gray-50/50 text-center text-sm text-gray-400">
            No transactions in this statement
          </td>
        </tr>
      )}
    </>
  );
}
