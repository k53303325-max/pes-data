"use client";

import Link from "next/link";
import { Logo } from "@/components/ui/Logo";
import { Button } from "@/components/ui/Button";
import { Menu, X } from "lucide-react";
import { useState } from "react";

export function Header() {
  const [open, setOpen] = useState(false);

  return (
    <header className="fixed top-0 left-0 right-0 z-50 glass">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Logo />

          <nav className="hidden md:flex items-center gap-8">
            <a href="#how" className="text-sm text-white/70 hover:text-white transition-colors">
              Как работает
            </a>
            <a href="#pricing" className="text-sm text-white/70 hover:text-white transition-colors">
              Тарифы
            </a>
            <a href="#benefits" className="text-sm text-white/70 hover:text-white transition-colors">
              Преимущества
            </a>
            <a href="#contact" className="text-sm text-white/70 hover:text-white transition-colors">
              Заявка
            </a>
          </nav>

          <div className="hidden md:flex items-center gap-3">
            <Link href="/login">
              <Button variant="ghost" size="sm">Войти</Button>
            </Link>
            <Link href="/register">
              <Button size="sm">Запустить тест</Button>
            </Link>
          </div>

          <button
            className="md:hidden p-2 text-white/70"
            onClick={() => setOpen(!open)}
            aria-label="Меню"
          >
            {open ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>

        {open && (
          <div className="md:hidden pb-4 space-y-3 border-t border-white/10 pt-4">
            <a href="#how" className="block text-sm text-white/70" onClick={() => setOpen(false)}>Как работает</a>
            <a href="#pricing" className="block text-sm text-white/70" onClick={() => setOpen(false)}>Тарифы</a>
            <a href="#benefits" className="block text-sm text-white/70" onClick={() => setOpen(false)}>Преимущества</a>
            <a href="#contact" className="block text-sm text-white/70" onClick={() => setOpen(false)}>Заявка</a>
            <div className="flex gap-2 pt-2">
              <Link href="/login" className="flex-1">
                <Button variant="secondary" size="sm" className="w-full">Войти</Button>
              </Link>
              <Link href="/register" className="flex-1">
                <Button size="sm" className="w-full">Тест</Button>
              </Link>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
