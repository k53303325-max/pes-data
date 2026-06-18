import { Bell, Layers, Key, EyeOff, HeadphonesIcon, RefreshCw } from "lucide-react";

const benefits = [
  {
    icon: Bell,
    title: "Мгновенные уведомления",
    desc: "Telegram-бот сообщает о каждом новом лиде в реальном времени",
  },
  {
    icon: Layers,
    title: "Кластеры контактов",
    desc: "Основной + 3 кластера с отдельными лимитами и статистикой",
  },
  {
    icon: Key,
    title: "API и Webhook",
    desc: "Интеграция с Bitrix24, amoCRM и вашими системами",
  },
  {
    icon: EyeOff,
    title: "White-label",
    desc: "Скрывайте бренд Пёс Дата для своих клиентов-реселлеров",
  },
  {
    icon: HeadphonesIcon,
    title: "Обучение и FAQ",
    desc: "Гайды по недозвонам, конверсии и легальности работы",
  },
  {
    icon: RefreshCw,
    title: "Ручная конверсия",
    desc: "Вы сами отмечаете успешные контакты — мы считаем статистику",
  },
];

export function Benefits() {
  return (
    <section id="benefits" className="py-20 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-14">
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">Преимущества</h2>
          <p className="text-white/60">Всё для эффективной работы с лидами</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {benefits.map(({ icon: Icon, title, desc }) => (
            <div key={title} className="glass rounded-2xl p-6 card-hover">
              <div className="w-10 h-10 rounded-lg bg-brand-purple/20 flex items-center justify-center mb-4">
                <Icon size={20} className="text-brand-purple" />
              </div>
              <h3 className="font-semibold mb-2">{title}</h3>
              <p className="text-sm text-white/50 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
