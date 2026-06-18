import { Globe, Search, Phone, BarChart3 } from "lucide-react";

const steps = [
  {
    icon: Globe,
    step: "01",
    title: "Добавьте домены конкурентов",
    desc: "Укажите сайты, с которых хотите получать контакты посетителей",
  },
  {
    icon: Search,
    step: "02",
    title: "Мы собираем данные",
    desc: "Поставщик данных определяет посетителей и передаёт номера через webhook",
  },
  {
    icon: Phone,
    step: "03",
    title: "Получайте номера",
    desc: "Лиды появляются в личном кабинете и приходят в Telegram",
  },
  {
    icon: BarChart3,
    step: "04",
    title: "Звоните и считайте конверсию",
    desc: "Отмечайте успешные контакты — система считает вашу конверсию",
  },
];

export function HowItWorks() {
  return (
    <section id="how" className="py-20 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-14">
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">Как это работает</h2>
          <p className="text-white/60 max-w-xl mx-auto">
            Четыре простых шага от настройки до первых звонков
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {steps.map(({ icon: Icon, step, title, desc }) => (
            <div key={step} className="glass rounded-2xl p-6 card-hover relative">
              <div className="text-5xl font-bold text-brand-purple/20 absolute top-4 right-4">
                {step}
              </div>
              <div className="w-12 h-12 rounded-xl bg-brand-purple/20 flex items-center justify-center mb-4">
                <Icon size={22} className="text-brand-purple" />
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
