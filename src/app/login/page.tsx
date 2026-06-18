"use client";

import { useState } from "react";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Logo } from "@/components/ui/Logo";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { toast } from "sonner";

export default function LoginPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ email: "", password: "" });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);

    const result = await signIn("credentials", {
      email: form.email,
      password: form.password,
      redirect: false,
    });

    setLoading(false);

    if (result?.error) {
      toast.error("Неверный email или пароль");
      return;
    }

    toast.success("Добро пожаловать!");
    router.push("/dashboard");
    router.refresh();
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-gradient-to-br from-brand-purple/10 via-transparent to-brand-dark pointer-events-none" />

      <div className="w-full max-w-md relative">
        <div className="text-center mb-8">
          <Logo className="justify-center mb-6" />
          <h1 className="text-2xl font-bold">Вход в кабинет</h1>
          <p className="text-white/50 text-sm mt-2">Управляйте лидами и проектами</p>
        </div>

        <form onSubmit={handleSubmit} className="glass rounded-2xl p-8 space-y-4">
          <Input
            label="Email"
            id="email"
            type="email"
            required
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            placeholder="demo@pesdata.ru"
          />
          <Input
            label="Пароль"
            id="password"
            type="password"
            required
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            placeholder="••••••••"
          />
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Вход..." : "Войти"}
          </Button>
        </form>

        <p className="text-center text-sm text-white/50 mt-6">
          Нет аккаунта?{" "}
          <Link href="/register" className="text-brand-purple hover:underline">
            Зарегистрироваться
          </Link>
        </p>

        <p className="text-center text-xs text-white/30 mt-4">
          Демо: demo@pesdata.ru / demo123
        </p>
      </div>
    </div>
  );
}
