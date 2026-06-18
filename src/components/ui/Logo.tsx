import { cn } from "@/lib/utils";
import Image from "next/image";
import Link from "next/link";

interface LogoProps {
  className?: string;
  showText?: boolean;
  size?: "sm" | "md" | "lg";
}

const sizes = {
  sm: 32,
  md: 40,
  lg: 56,
};

export function Logo({ className, showText = true, size = "md" }: LogoProps) {
  const px = sizes[size];

  return (
    <Link href="/" className={cn("flex items-center gap-3 group", className)}>
      <div className="relative shrink-0" style={{ width: px, height: px }}>
        <Image
          src="/assets/logo.png"
          alt="Пёс Дата"
          width={px}
          height={px}
          className="object-contain"
          priority
        />
      </div>
      {showText && (
        <span className="font-bold text-white tracking-tight">
          <span className="text-brand-purple">Пёс</span> Дата
        </span>
      )}
    </Link>
  );
}
