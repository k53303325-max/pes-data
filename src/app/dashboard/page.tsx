import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";
import { authOptions } from "@/lib/auth";
import { DashboardLayout } from "@/components/dashboard/DashboardLayout";
import { DashboardView } from "@/components/dashboard/DashboardView";

export default async function DashboardPage() {
  const session = await getServerSession(authOptions);
  if (!session) redirect("/login");

  return (
    <DashboardLayout>
      <DashboardView />
    </DashboardLayout>
  );
}
