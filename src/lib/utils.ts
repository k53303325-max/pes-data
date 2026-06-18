import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPhone(phone: string): string {
  const digits = phone.replace(/\D/g, "");
  if (digits.length === 11 && digits.startsWith("7")) {
    return `+7 (${digits.slice(1, 4)}) ${digits.slice(4, 7)}-${digits.slice(7, 9)}-${digits.slice(9, 11)}`;
  }
  return phone;
}

export function formatDate(date: Date | string): string {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(date));
}

export const PLANS = {
  TEST: { name: "Тест", price: 40, contacts: 100 },
  START: { name: "Старт", price: 30, contacts: 1000 },
  STANDARD: { name: "Стандарт", price: 25, contacts: 3000 },
  PRO: { name: "Профи", price: 17, contacts: 9000 },
  MAX: { name: "Макси", price: 15, contacts: 42000 },
} as const;

export const CLUSTER_LABELS: Record<string, string> = {
  MAIN: "Основной",
  CLUSTER_1: "Кластер 1",
  CLUSTER_2: "Кластер 2",
  CLUSTER_3: "Кластер 3",
};

export const LEAD_STATUS_LABELS: Record<string, string> = {
  NEW: "Новый",
  CONTACTED: "Обработан",
  SUCCESS: "Успех",
  FAILED: "Недозвон",
};

export const LEAD_STATUS_COLORS: Record<string, string> = {
  NEW: "bg-brand-purple/20 text-brand-accent",
  CONTACTED: "bg-yellow-500/20 text-yellow-300",
  SUCCESS: "bg-green-500/20 text-green-300",
  FAILED: "bg-red-500/20 text-red-300",
};
