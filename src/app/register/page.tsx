"use client";

import { useState } from "react";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Logo } from "@/components/ui/Logo";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { toast } from "sonner";

export default function RegisterPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    name: "",
    email: "",
    phone: "",
    password: "",
  });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);

    try {
      const res = await fetch("/api/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });

      const data = await res.json();

      if (!res.ok) {
        toast.error(data.error || "Ошибка регистрации");
        setLoading(false);
        return;
      }

      const result = await signIn("credentials", {
        email: form.email,
        password: form.password,
        redirect: false,
      });

      if (result?.error) {
        toast.error("Аккаунт создан, но вход не удался");
        router.push("/login");
        return;
      }

      toast.success("Добро пожаловать в Пёс Дата!");
      router.push("/dashboard");
      router.refresh();
    } catch {
      toast.error("Ошибка регистрации");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12">
      <div className="absolute inset-0 bg-gradient-to-br from-brand-purple/10 via-transparent to-brand-dark pointer-events-none" />

      <div className="w-full max-w-md relative">
        <div className="text-center mb-8">
          <Logo className="justify-center mb-6" />
          <h1 className="text-2xl font-bold">Запустить тест</h1>
          <p className="text-white/50 text-sm mt-2">100 контактов в подарок при регистрации</p>
        </div>

        <form onSubmit={handleSubmit} className="glass rounded-2xl p-8 space-y-4">
          <Input
            label="Имя"
            id="name"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="Иван Иванов"
          />
          <Input
            label="Email"
            id="email"
            type="email"
            required
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
          <Input
            label="Телефон"
            id="phone"
            type="tel"
            required
            value={form.phone}
            onChange={(e) => setForm({ ...form, phone: e.target.value })}
            placeholder="+7 (900) 123-45-67"
          />
          <Input
            label="Пароль"
            id="password"
            type="password"
            required
            minLength={6}
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
          <Button type="submit" className="w-full" size="lg" disabled={loading}>
            {loading ? "Создание..." : "Создать аккаунт"}
          </Button>
        </form>

        <p className="text-center text-sm text-white/50 mt-6">
          Уже есть аккаунт?{" "}
          <Link href="/login" className="text-brand-purple hover:underline">
            Войти
          </Link>
        </p>
      </div>
    </div>
  );
}
