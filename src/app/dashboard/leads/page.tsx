import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";
import { authOptions } from "@/lib/auth";
import { DashboardLayout } from "@/components/dashboard/DashboardLayout";
import { LeadsView } from "@/components/dashboard/LeadsView";

export default async function LeadsPage() {
  const session = await getServerSession(authOptions);
  if (!session) redirect("/login");

  return (
    <DashboardLayout>
      <LeadsView />
    </DashboardLayout>
  );
}
