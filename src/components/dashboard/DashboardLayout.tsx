"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut, useSession } from "next-auth/react";
import { Logo } from "@/components/ui/Logo";
import { Button } from "@/components/ui/Button";
import { cn, PLANS } from "@/lib/utils";
import {
  LayoutDashboard,
  Phone,
  FolderKanban,
  Globe,
  Layers,
  Wallet,
  Plug,
  BookOpen,
  LogOut,
  Menu,
  X,
  Shield,
} from "lucide-react";
import { useState } from "react";

const navItems = [
  { href: "/dashboard", label: "Дашборд", icon: LayoutDashboard },
  { href: "/dashboard/leads", label: "Лента номеров", icon: Phone },
  { href: "/dashboard/projects", label: "Проекты", icon: FolderKanban },
  { href: "/dashboard/sources", label: "Источники", icon: Globe },
  { href: "/dashboard/clusters", label: "Кластеры", icon: Layers },
  { href: "/dashboard/finance", label: "Финансы", icon: Wallet },
  { href: "/dashboard/integrations", label: "Интеграции", icon: Plug },
  { href: "/dashboard/training", label: "Обучение", icon: BookOpen },
];

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { data: session } = useSession();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const planKey = (session?.user?.plan || "TEST") as keyof typeof PLANS;
  const planName = PLANS[planKey]?.name || "Тест";

  return (
    <div className="min-h-screen flex">
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside
        className={cn(
          "fixed lg:static inset-y-0 left-0 z-50 w-64 bg-brand-dark border-r border-white/10 flex flex-col transition-transform duration-300",
          sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        <div className="p-4 border-b border-white/10">
          <Logo size="sm" />
        </div>

        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {navItems.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                onClick={() => setSidebarOpen(false)}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-colors",
                  active
                    ? "bg-brand-purple/20 text-brand-accent"
                    : "text-white/60 hover:text-white hover:bg-white/5"
                )}
              >
                <Icon size={18} />
                {label}
              </Link>
            );
          })}

          {session?.user?.role === "ADMIN" && (
            <Link
              href="/admin"
              className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-yellow-400/80 hover:bg-yellow-400/10"
            >
              <Shield size={18} />
              Админ-панель
            </Link>
          )}
        </nav>

        <div className="p-4 border-t border-white/10 space-y-3">
          <div className="glass rounded-xl p-3">
            <div className="text-xs text-white/40 mb-1">Баланс</div>
            <div className="text-xl font-bold text-brand-accent">
              {(session?.user?.balance ?? 0).toLocaleString("ru-RU")} конт.
            </div>
            <div className="text-xs text-white/40 mt-1">Тариф: {planName}</div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start"
            onClick={() => signOut({ callbackUrl: "/" })}
          >
            <LogOut size={16} />
            Выйти
          </Button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="lg:hidden flex items-center justify-between p-4 border-b border-white/10">
          <button onClick={() => setSidebarOpen(true)} aria-label="Меню">
            <Menu size={24} />
          </button>
          <Logo showText={false} size="sm" />
          <button onClick={() => setSidebarOpen(false)} className="opacity-0 pointer-events-none">
            <X size={24} />
          </button>
        </header>

        <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-auto">{children}</main>
      </div>
    </div>
  );
}
