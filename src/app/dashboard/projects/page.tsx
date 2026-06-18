import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";
import { authOptions } from "@/lib/auth";
import { DashboardLayout } from "@/components/dashboard/DashboardLayout";
import { Construction } from "lucide-react";

function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] text-center">
      <Construction size={48} className="text-brand-purple/50 mb-4" />
      <h1 className="text-2xl font-bold mb-2">{title}</h1>
      <p className="text-white/50">Раздел в разработке</p>
    </div>
  );
}

async function ProtectedPage({ title }: { title: string }) {
  const session = await getServerSession(authOptions);
  if (!session) redirect("/login");

  return (
    <DashboardLayout>
      <PlaceholderPage title={title} />
    </DashboardLayout>
  );
}

export default async function ProjectsPage() {
  return ProtectedPage({ title: "Проекты" });
}
