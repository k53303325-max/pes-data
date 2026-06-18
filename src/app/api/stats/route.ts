import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

export async function GET(req: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { searchParams } = new URL(req.url);
  const projectId = searchParams.get("projectId");
  const period = searchParams.get("period") || "week";

  const projects = await prisma.project.findMany({
    where: {
      userId: session.user.id,
      ...(projectId ? { id: projectId } : {}),
    },
    select: { id: true },
  });

  const projectIds = projects.map((p) => p.id);

  const now = new Date();
  let startDate = new Date();
  if (period === "day") {
    startDate.setDate(now.getDate() - 1);
  } else if (period === "week") {
    startDate.setDate(now.getDate() - 7);
  } else {
    startDate.setMonth(now.getMonth() - 1);
  }

  const [totalLeads, periodLeads, byStatus, byCluster, byDay] = await Promise.all([
    prisma.lead.count({ where: { projectId: { in: projectIds } } }),
    prisma.lead.count({
      where: {
        projectId: { in: projectIds },
        createdAt: { gte: startDate },
      },
    }),
    prisma.lead.groupBy({
      by: ["status"],
      where: { projectId: { in: projectIds } },
      _count: true,
    }),
    prisma.lead.groupBy({
      by: ["cluster"],
      where: { projectId: { in: projectIds } },
      _count: true,
    }),
    prisma.$queryRaw<Array<{ date: string; count: bigint }>>`
      SELECT DATE("createdAt") as date, COUNT(*)::int as count
      FROM "Lead"
      WHERE "projectId" = ANY(${projectIds})
        AND "createdAt" >= ${startDate}
      GROUP BY DATE("createdAt")
      ORDER BY date ASC
    `.catch(() => []),
  ]);

  const successCount =
    byStatus.find((s) => s.status === "SUCCESS")?._count || 0;
  const conversionRate =
    totalLeads > 0 ? Math.round((successCount / totalLeads) * 1000) / 10 : 0;

  return NextResponse.json({
    totalLeads,
    periodLeads,
    conversionRate,
    byStatus: byStatus.map((s) => ({ status: s.status, count: s._count })),
    byCluster: byCluster.map((c) => ({ cluster: c.cluster, count: c._count })),
    chartData: Array.isArray(byDay)
      ? byDay.map((d) => ({
          date: d.date,
          count: Number(d.count),
        }))
      : [],
    balance: session.user.balance,
  });
}
