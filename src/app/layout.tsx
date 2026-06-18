import { Inter } from "next/font/google";
import "./globals.css";
import { ToastProvider } from "@/components/ui/ToastProvider";
import { Providers } from "./providers";

const inter = Inter({
  subsets: ["latin", "cyrillic"],
  variable: "--font-inter",
});

export const metadata = {
  title: "Пёс Дата — платформа лидогенерации",
  description:
    "Определяем посетителей сайтов конкурентов и передаём вам их номера телефонов",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru" className="dark">
      <body className={`${inter.variable} font-sans antialiased bg-brand-dark text-brand-light min-h-screen`}>
        <Providers>
          {children}
          <ToastProvider />
        </Providers>
      </body>
    </html>
  );
}
