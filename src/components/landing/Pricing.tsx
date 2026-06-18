import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Check } from "lucide-react";
import { PLANS } from "@/lib/utils";

const planOrder = ["TEST", "START", "STANDARD", "PRO", "MAX"] as const;

export function Pricing() {
  return (
    <section id="pricing" className="py-20 px-4 sm:px-6 lg:px-8 bg-white/[0.02]">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-14">
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">Тарифы</h2>
          <p className="text-white/60">Платите только за контакты. Без абонентской платы.</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {planOrder.map((key, i) => {
            const plan = PLANS[key];
            const isPopular = key === "START";

            return (
              <div
                key={key}
                className={`glass rounded-2xl p-6 card-hover relative flex flex-col ${
                  isPopular ? "border-brand-purple/50 ring-1 ring-brand-purple/30" : ""
                }`}
              >
                {isPopular && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 bg-brand-purple text-xs font-semibold rounded-full">
                    Популярный
                  </span>
                )}
                <h3 className="font-bold text-lg mb-1">{plan.name}</h3>
                <div className="mb-4">
                  <span className="text-3xl font-bold">{plan.price}₽</span>
                  <span className="text-white/50 text-sm"> / 100 шт</span>
                </div>
                <p className="text-sm text-white/50 mb-6">
                  Пакет {plan.contacts.toLocaleString("ru-RU")} контактов
                </p>
                <ul className="space-y-2 mb-6 flex-1">
                  {["Webhook API", "Telegram-уведомления", "Статистика", "Кластеры"].map((f) => (
                    <li key={f} className="flex items-center gap-2 text-sm text-white/70">
                      <Check size={14} className="text-brand-purple shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Link href="/register">
                  <Button
                    variant={isPopular ? "primary" : "secondary"}
                    className="w-full"
                    size="sm"
                  >
                    {i === 0 ? "Запустить тест" : "Выбрать"}
                  </Button>
                </Link>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
