import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";
import { authOptions } from "@/lib/auth";
import { DashboardLayout } from "@/components/dashboard/DashboardLayout";
import { Construction } from "lucide-react";

export default async function FinancePage() {
  const session = await getServerSession(authOptions);
  if (!session) redirect("/login");

  return (
    <DashboardLayout>
      <div className="flex flex-col items-center justify-center min-h-[50vh] text-center">
        <Construction size={48} className="text-brand-purple/50 mb-4" />
        <h1 className="text-2xl font-bold mb-2">Финансы</h1>
        <p className="text-white/50">Раздел в разработке</p>
      </div>
    </DashboardLayout>
  );
}
