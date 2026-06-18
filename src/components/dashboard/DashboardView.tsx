"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from "recharts";
import { DashboardSkeleton } from "@/components/ui/Skeleton";
import { Phone, TrendingUp, Users, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

interface Stats {
  totalLeads: number;
  periodLeads: number;
  conversionRate: number;
  balance: number;
  byStatus: Array<{ status: string; count: number }>;
  byCluster: Array<{ cluster: string; count: number }>;
  chartData: Array<{ date: string; count: number }>;
}

const PERIODS = [
  { value: "day", label: "День" },
  { value: "week", label: "Неделя" },
  { value: "month", label: "Месяц" },
];

export function DashboardView() {
  const { data: session } = useSession();
  const [stats, setStats] = useState<Stats | null>(null);
  const [period, setPeriod] = useState("week");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const res = await fetch(`/api/stats?period=${period}`);
        if (res.ok) {
          setStats(await res.json());
        }
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [period]);

  if (loading) return <DashboardSkeleton />;

  const cards = [
    {
      label: "Баланс контактов",
      value: (stats?.balance ?? session?.user?.balance ?? 0).toLocaleString("ru-RU"),
      suffix: "шт",
      icon: Zap,
      color: "text-brand-purple",
    },
    {
      label: "Всего лидов",
      value: (stats?.totalLeads ?? 0).toLocaleString("ru-RU"),
      icon: Phone,
      color: "text-green-400",
    },
    {
      label: "За период",
      value: (stats?.periodLeads ?? 0).toLocaleString("ru-RU"),
      icon: Users,
      color: "text-blue-400",
    },
    {
      label: "Конверсия",
      value: `${stats?.conversionRate ?? 0}%`,
      icon: TrendingUp,
      color: "text-yellow-400",
    },
  ];

  const statusLabels: Record<string, string> = {
    NEW: "Новые",
    CONTACTED: "Обработаны",
    SUCCESS: "Успех",
    FAILED: "Недозвон",
  };

  const clusterLabels: Record<string, string> = {
    MAIN: "Основной",
    CLUSTER_1: "Кл. 1",
    CLUSTER_2: "Кл. 2",
    CLUSTER_3: "Кл. 3",
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Дашборд</h1>
          <p className="text-white/50 text-sm mt-1">
            Привет, {session?.user?.name || "клиент"}!
          </p>
        </div>

        <div className="flex gap-2">
          {PERIODS.map((p) => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={cn(
                "px-3 py-1.5 rounded-lg text-sm transition-colors",
                period === p.value
                  ? "bg-brand-purple text-white"
                  : "bg-white/5 text-white/60 hover:text-white"
              )}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map(({ label, value, suffix, icon: Icon, color }) => (
          <div key={label} className="glass rounded-2xl p-5 card-hover">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm text-white/50">{label}</span>
              <Icon size={18} className={color} />
            </div>
            <div className="text-2xl font-bold">
              {value}
              {suffix && <span className="text-sm text-white/40 ml-1">{suffix}</span>}
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 glass rounded-2xl p-5">
          <h2 className="font-semibold mb-4">Лиды за период</h2>
          <div className="h-64">
            {stats?.chartData && stats.chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={stats.chartData}>
                  <defs>
                    <linearGradient id="colorLeads" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#5B5FC7" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#5B5FC7" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis
                    dataKey="date"
                    stroke="rgba(255,255,255,0.3)"
                    tick={{ fontSize: 11 }}
                    tickFormatter={(v) =>
                      new Date(v).toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit" })
                    }
                  />
                  <YAxis stroke="rgba(255,255,255,0.3)" tick={{ fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      background: "#1E1E3A",
                      border: "1px solid rgba(91,95,199,0.3)",
                      borderRadius: "8px",
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="count"
                    stroke="#5B5FC7"
                    fill="url(#colorLeads)"
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-white/30 text-sm">
                Нет данных за выбранный период
              </div>
            )}
          </div>
        </div>

        <div className="glass rounded-2xl p-5">
          <h2 className="font-semibold mb-4">По статусам</h2>
          <div className="h-64">
            {stats?.byStatus && stats.byStatus.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stats.byStatus.map((s) => ({
                  name: statusLabels[s.status] || s.status,
                  count: s.count,
                }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="name" stroke="rgba(255,255,255,0.3)" tick={{ fontSize: 10 }} />
                  <YAxis stroke="rgba(255,255,255,0.3)" tick={{ fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      background: "#1E1E3A",
                      border: "1px solid rgba(91,95,199,0.3)",
                      borderRadius: "8px",
                    }}
                  />
                  <Bar dataKey="count" fill="#5B5FC7" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-white/30 text-sm">
                Нет данных
              </div>
            )}
          </div>
        </div>
      </div>

      {stats?.byCluster && stats.byCluster.length > 0 && (
        <div className="glass rounded-2xl p-5">
          <h2 className="font-semibold mb-4">По кластерам</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {stats.byCluster.map((c) => (
              <div key={c.cluster} className="bg-white/5 rounded-xl p-4 text-center">
                <div className="text-2xl font-bold text-brand-accent">{c.count}</div>
                <div className="text-xs text-white/50 mt-1">
                  {clusterLabels[c.cluster] || c.cluster}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
