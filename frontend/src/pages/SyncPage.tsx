import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  RefreshCw,
  Check,
  X,
  Circle,
  Loader2,
  AlertTriangle,
  Mail,
  Calendar,
} from 'lucide-react';
import { getSyncStatus, syncMonth, resyncMonth } from '../api/sync';
import type { SyncMonth } from '../types';
import LoadingSpinner from '../components/LoadingSpinner';
import { formatMonth } from '../utils/formatters';

export default function SyncPage() {
  const queryClient = useQueryClient();
  const [syncingMonths, setSyncingMonths] = useState<Set<string>>(new Set());
  const [confirmResync, setConfirmResync] = useState<string | null>(null);

  const { data: status, isLoading } = useQuery({
    queryKey: ['sync-status'],
    queryFn: getSyncStatus,
  });

  const syncMutation = useMutation({
    mutationFn: (month: string) => syncMonth(month),
    onMutate: (month) => {
      setSyncingMonths((prev) => new Set(prev).add(month));
    },
    onSettled: (_, __, month) => {
      setSyncingMonths((prev) => {
        const next = new Set(prev);
        next.delete(month);
        return next;
      });
      queryClient.invalidateQueries({ queryKey: ['sync-status'] });
    },
  });

  const resyncMutation = useMutation({
    mutationFn: (month: string) => resyncMonth(month),
    onMutate: (month) => {
      setSyncingMonths((prev) => new Set(prev).add(month));
    },
    onSettled: (_, __, month) => {
      setSyncingMonths((prev) => {
        const next = new Set(prev);
        next.delete(month);
        return next;
      });
      setConfirmResync(null);
      queryClient.invalidateQueries({ queryKey: ['sync-status'] });
    },
  });

  const handleSyncAll = async () => {
    const unsynced = (status?.months || []).filter((m) => {
      const s = normalizeStatus(m.sync_status);
      return s === 'not_synced' || s === 'failed';
    });
    for (const m of unsynced) {
      syncMutation.mutate(m.month);
    }
  };

  /** Normalize sync_status to lowercase for consistent comparison */
  const normalizeStatus = (status: string | null | undefined): string => {
    if (!status) return 'not_synced';
    return status.toLowerCase();
  };

  const getStatusIcon = (month: SyncMonth, isSyncing: boolean) => {
    if (isSyncing) {
      return <Loader2 size={20} className="animate-spin text-yellow-500" />;
    }
    const status = normalizeStatus(month.sync_status);
    switch (status) {
      case 'completed':
        return <Check size={20} className="text-green-500" />;
      case 'in_progress':
        return <Loader2 size={20} className="animate-spin text-yellow-500" />;
      case 'failed':
        return <X size={20} className="text-red-500" />;
      case 'partial':
        return <AlertTriangle size={20} className="text-yellow-500" />;
      default:
        return <Circle size={20} className="text-gray-300" />;
    }
  };

  const getStatusBg = (status: string | null, isSyncing: boolean) => {
    if (isSyncing) return 'border-yellow-200 bg-yellow-50/50';
    switch (normalizeStatus(status)) {
      case 'completed':
        return 'border-green-200 bg-green-50/30';
      case 'failed':
        return 'border-red-200 bg-red-50/30';
      default:
        return 'border-gray-200 bg-white';
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full py-32">
        <LoadingSpinner size={40} text="Loading sync status..." />
      </div>
    );
  }

  const months = status?.months || [];
  const unsyncedCount = months.filter((m) => {
    const s = normalizeStatus(m.sync_status);
    return s === 'not_synced' || s === 'failed';
  }).length;

  return (
    <div className="p-4 lg:p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Sync Bank Statements</h1>
          <p className="text-sm text-gray-500 mt-1">
            Parse your bank statement emails to extract transactions
          </p>
        </div>
        {unsyncedCount > 0 && (
          <button
            onClick={handleSyncAll}
            disabled={syncMutation.isPending}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={16} />
            Sync All Unsynced ({unsyncedCount})
          </button>
        )}
      </div>

      {/* Month grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {months.map((month) => {
          const isSyncing = syncingMonths.has(month.month);
          return (
            <div
              key={month.month}
              className={`rounded-xl border p-4 transition-all ${getStatusBg(
                month.sync_status,
                isSyncing
              )}`}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Calendar size={16} className="text-gray-400" />
                  <h3 className="text-sm font-semibold text-gray-900">
                    {formatMonth(month.month)}
                  </h3>
                </div>
                {getStatusIcon(month, isSyncing)}
              </div>

              {normalizeStatus(month.sync_status) === 'completed' && (
                <div className="space-y-1.5 mb-3">
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <Mail size={12} />
                    <span>{month.emails_found} emails found</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <Check size={12} />
                    <span>{month.transactions_created} transactions</span>
                  </div>
                  {month.last_synced && (
                    <p className="text-xs text-gray-400">
                      Last synced:{' '}
                      {new Date(month.last_synced).toLocaleDateString('en-IN', {
                        day: 'numeric',
                        month: 'short',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </p>
                  )}
                </div>
              )}

              {normalizeStatus(month.sync_status) === 'failed' && (
                <div className="flex items-center gap-1.5 mb-3 text-xs text-red-500">
                  <AlertTriangle size={12} />
                  <span>Sync failed</span>
                </div>
              )}

              <div className="flex gap-2">
                {(['not_synced', 'failed'].includes(normalizeStatus(month.sync_status))) && (
                  <button
                    onClick={() => syncMutation.mutate(month.month)}
                    disabled={isSyncing}
                    className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-indigo-600 text-white text-xs font-medium rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50"
                  >
                    {isSyncing ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : (
                      <RefreshCw size={14} />
                    )}
                    {isSyncing ? 'Syncing...' : 'Sync'}
                  </button>
                )}

                {normalizeStatus(month.sync_status) === 'completed' && (
                  <button
                    onClick={() => setConfirmResync(month.month)}
                    disabled={isSyncing}
                    className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-white border border-gray-200 text-gray-700 text-xs font-medium rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
                  >
                    <RefreshCw size={14} />
                    Re-sync
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {months.length === 0 && (
        <div className="text-center py-16 text-gray-400">
          <Calendar size={40} className="mx-auto mb-3 opacity-50" />
          <p className="text-sm">No months available to sync</p>
        </div>
      )}

      {/* Confirm re-sync dialog */}
      {confirmResync && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-xl shadow-xl p-6 max-w-sm w-full mx-4">
            <div className="flex items-center gap-3 mb-4">
              <div className="bg-yellow-50 rounded-full p-2">
                <AlertTriangle size={20} className="text-yellow-600" />
              </div>
              <h3 className="text-base font-semibold text-gray-900">Confirm Re-sync</h3>
            </div>
            <p className="text-sm text-gray-600 mb-6">
              This will delete existing transactions for{' '}
              <strong>{formatMonth(confirmResync)}</strong> and re-parse all emails. This cannot be
              undone.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setConfirmResync(null)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => resyncMutation.mutate(confirmResync)}
                disabled={resyncMutation.isPending}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
              >
                {resyncMutation.isPending ? 'Re-syncing...' : 'Re-sync'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
