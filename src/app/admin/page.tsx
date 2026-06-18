import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";
import { authOptions } from "@/lib/auth";
import { DashboardLayout } from "@/components/dashboard/DashboardLayout";

export default async function AdminPage() {
  const session = await getServerSession(authOptions);
  if (!session) redirect("/login");
  if (session.user.role !== "ADMIN") redirect("/dashboard");

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Панель администратора</h1>
        <p className="text-white/50">Управление клиентами, балансами и источниками данных</p>
        <div className="glass rounded-2xl p-8 text-center text-white/40">
          Админ-панель в разработке
        </div>
      </div>
    </DashboardLayout>
  );
}
