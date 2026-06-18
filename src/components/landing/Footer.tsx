import { Logo } from "@/components/ui/Logo";

export function Footer() {
  return (
    <footer className="border-t border-white/10 py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
        <Logo />
        <p className="text-sm text-white/40">
          © {new Date().getFullYear()} Пёс Дата. Все права защищены.
        </p>
        <div className="flex gap-6 text-sm text-white/40">
          <a href="#" className="hover:text-white/70 transition-colors">Политика</a>
          <a href="#" className="hover:text-white/70 transition-colors">Оферта</a>
        </div>
      </div>
    </footer>
  );
}
