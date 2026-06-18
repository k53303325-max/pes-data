"use client";

import { useEffect, useState, useCallback } from "react";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { Button } from "@/components/ui/Button";
import {
  formatPhone,
  formatDate,
  CLUSTER_LABELS,
  LEAD_STATUS_LABELS,
  LEAD_STATUS_COLORS,
  cn,
} from "@/lib/utils";
import { ChevronLeft, ChevronRight, Filter, CheckCircle } from "lucide-react";
import { toast } from "sonner";

interface Lead {
  id: string;
  phone: string;
  source: string;
  cluster: string;
  status: string;
  createdAt: string;
}

interface Pagination {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
}

export function LeadsView() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [pagination, setPagination] = useState<Pagination>({
    page: 1,
    limit: 20,
    total: 0,
    totalPages: 0,
  });
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    status: "",
    cluster: "",
    source: "",
  });
  const [showFilters, setShowFilters] = useState(false);

  const loadLeads = useCallback(async (page = 1) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(page), limit: "20" });
      if (filters.status) params.set("status", filters.status);
      if (filters.cluster) params.set("cluster", filters.cluster);
      if (filters.source) params.set("source", filters.source);

      const res = await fetch(`/api/leads?${params}`);
      if (res.ok) {
        const data = await res.json();
        setLeads(data.leads);
        setPagination(data.pagination);
      }
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadLeads(1);
  }, [loadLeads]);

  async function updateStatus(id: string, status: string) {
    const res = await fetch("/api/leads", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, status }),
    });

    if (res.ok) {
      setLeads((prev) =>
        prev.map((l) => (l.id === id ? { ...l, status } : l))
      );
      toast.success("Статус обновлён");
    } else {
      toast.error("Ошибка обновления");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Лента номеров</h1>
          <p className="text-white/50 text-sm mt-1">
            Всего: {pagination.total.toLocaleString("ru-RU")} контактов
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => setShowFilters(!showFilters)}
        >
          <Filter size={16} />
          Фильтры
        </Button>
      </div>

      {showFilters && (
        <div className="glass rounded-xl p-4 grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="text-xs text-white/50 block mb-1">Статус</label>
            <select
              value={filters.status}
              onChange={(e) => setFilters({ ...filters, status: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm"
            >
              <option value="">Все</option>
              {Object.entries(LEAD_STATUS_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-white/50 block mb-1">Кластер</label>
            <select
              value={filters.cluster}
              onChange={(e) => setFilters({ ...filters, cluster: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm"
            >
              <option value="">Все</option>
              {Object.entries(CLUSTER_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-white/50 block mb-1">Источник</label>
            <input
              value={filters.source}
              onChange={(e) => setFilters({ ...filters, source: e.target.value })}
              placeholder="domain.ru"
              className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm"
            />
          </div>
        </div>
      )}

      {loading ? (
        <TableSkeleton rows={8} />
      ) : leads.length === 0 ? (
        <div className="glass rounded-2xl p-12 text-center text-white/40">
          Лиды не найдены. Добавьте источники и дождитесь первых контактов.
        </div>
      ) : (
        <>
          <div className="glass rounded-2xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10 text-white/50">
                    <th className="text-left p-4 font-medium">Номер</th>
                    <th className="text-left p-4 font-medium hidden sm:table-cell">Источник</th>
                    <th className="text-left p-4 font-medium hidden md:table-cell">Кластер</th>
                    <th className="text-left p-4 font-medium">Статус</th>
                    <th className="text-left p-4 font-medium hidden lg:table-cell">Дата</th>
                    <th className="text-right p-4 font-medium">Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {leads.map((lead) => (
                    <tr
                      key={lead.id}
                      className="border-b border-white/5 hover:bg-white/[0.02] transition-colors"
                    >
                      <td className="p-4 font-mono">{formatPhone(lead.phone)}</td>
                      <td className="p-4 text-white/70 hidden sm:table-cell">{lead.source}</td>
                      <td className="p-4 hidden md:table-cell">
                        <span className="text-xs px-2 py-1 rounded-full bg-white/5">
                          {CLUSTER_LABELS[lead.cluster] || lead.cluster}
                        </span>
                      </td>
                      <td className="p-4">
                        <span
                          className={cn(
                            "text-xs px-2 py-1 rounded-full",
                            LEAD_STATUS_COLORS[lead.status]
                          )}
                        >
                          {LEAD_STATUS_LABELS[lead.status] || lead.status}
                        </span>
                      </td>
                      <td className="p-4 text-white/50 hidden lg:table-cell">
                        {formatDate(lead.createdAt)}
                      </td>
                      <td className="p-4 text-right">
                        {lead.status !== "SUCCESS" && (
                          <button
                            onClick={() => updateStatus(lead.id, "SUCCESS")}
                            className="inline-flex items-center gap-1 text-xs text-green-400 hover:text-green-300 transition-colors"
                            title="Отметить успех"
                          >
                            <CheckCircle size={14} />
                            <span className="hidden sm:inline">Успех</span>
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {pagination.totalPages > 1 && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-white/40">
                Страница {pagination.page} из {pagination.totalPages}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={pagination.page <= 1}
                  onClick={() => loadLeads(pagination.page - 1)}
                >
                  <ChevronLeft size={16} />
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={pagination.page >= pagination.totalPages}
                  onClick={() => loadLeads(pagination.page + 1)}
                >
                  <ChevronRight size={16} />
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
