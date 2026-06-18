"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { toast } from "sonner";
import { Send } from "lucide-react";

export function ContactForm() {
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    name: "",
    phone: "",
    email: "",
    company: "",
    message: "",
  });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);

    try {
      const res = await fetch("/api/applications", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });

      if (!res.ok) throw new Error();

      toast.success("Заявка отправлена! Мы свяжемся с вами.");
      setForm({ name: "", phone: "", email: "", company: "", message: "" });
    } catch {
      toast.error("Ошибка отправки. Попробуйте позже.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section id="contact" className="py-20 px-4 sm:px-6 lg:px-8 bg-white/[0.02]">
      <div className="max-w-7xl mx-auto">
        <div className="max-w-xl mx-auto">
          <div className="text-center mb-10">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">Оставить заявку</h2>
            <p className="text-white/60">
              Расскажите о вашем бизнесе — поможем настроить первый проект
            </p>
          </div>

          <form onSubmit={handleSubmit} className="glass rounded-2xl p-6 sm:p-8 space-y-4">
            <Input
              label="Имя"
              id="name"
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Иван Иванов"
            />
            <Input
              label="Телефон"
              id="phone"
              required
              type="tel"
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
              placeholder="+7 (900) 123-45-67"
            />
            <Input
              label="Email"
              id="email"
              required
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              placeholder="mail@company.ru"
            />
            <Input
              label="Компания"
              id="company"
              value={form.company}
              onChange={(e) => setForm({ ...form, company: e.target.value })}
              placeholder="Название компании"
            />
            <div className="space-y-1.5">
              <label htmlFor="message" className="block text-sm text-white/70">
                Сообщение
              </label>
              <textarea
                id="message"
                rows={3}
                value={form.message}
                onChange={(e) => setForm({ ...form, message: e.target.value })}
                placeholder="Расскажите о вашей задаче..."
                className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-brand-purple/50 resize-none"
              />
            </div>
            <Button type="submit" className="w-full" size="lg" disabled={loading}>
              {loading ? "Отправка..." : "Отправить заявку"}
              <Send size={16} />
            </Button>
          </form>
        </div>
      </div>
    </section>
  );
}
