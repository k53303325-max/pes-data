import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { ArrowRight, TrendingUp, Shield, Zap } from "lucide-react";

export function Hero() {
  return (
    <section className="relative pt-32 pb-20 px-4 sm:px-6 lg:px-8 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-brand-purple/20 via-transparent to-brand-dark pointer-events-none" />
      <div className="absolute top-20 right-0 w-96 h-96 bg-brand-purple/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-72 h-72 bg-brand-accent/10 rounded-full blur-3xl pointer-events-none" />

      <div className="max-w-7xl mx-auto relative">
        <div className="max-w-3xl">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-brand-purple/20 border border-brand-purple/30 text-sm text-brand-accent mb-6">
            <Zap size={14} />
            Лидогенерация нового поколения
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight mb-6">
            Знайте, кто заходил к{" "}
            <span className="gradient-text">конкурентам</span>
          </h1>

          <p className="text-lg sm:text-xl text-white/60 mb-8 max-w-2xl leading-relaxed">
            Пёс Дата определяет посетителей сайтов конкурентов и передаёт вам их номера телефонов.
            Вы звоните первым — пока клиент ещё «горячий».
          </p>

          <div className="flex flex-col sm:flex-row gap-4 mb-12">
            <Link href="/register">
              <Button size="lg" className="w-full sm:w-auto">
                Запустить тест
                <ArrowRight size={18} />
              </Button>
            </Link>
            <a href="#how">
              <Button variant="secondary" size="lg" className="w-full sm:w-auto">
                Как это работает
              </Button>
            </a>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              { icon: TrendingUp, label: "Конверсия до 15%", desc: "Горячие лиды" },
              { icon: Shield, label: "White-label", desc: "Для реселлеров" },
              { icon: Zap, label: "От 40₽", desc: "За 100 контактов" },
            ].map(({ icon: Icon, label, desc }) => (
              <div key={label} className="glass rounded-xl p-4 card-hover">
                <Icon size={20} className="text-brand-purple mb-2" />
                <div className="font-semibold text-sm">{label}</div>
                <div className="text-xs text-white/50">{desc}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
