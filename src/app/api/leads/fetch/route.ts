import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

export async function POST(req: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { projectId, since } = await req.json();

  const project = await prisma.project.findFirst({
    where: { id: projectId, userId: session.user.id },
  });

  if (!project) {
    return NextResponse.json({ error: "Project not found" }, { status: 404 });
  }

  const where: Record<string, unknown> = { projectId };
  if (since) {
    where.createdAt = { gt: new Date(since) };
  }

  const leads = await prisma.lead.findMany({
    where,
    orderBy: { createdAt: "desc" },
    take: 100,
  });

  return NextResponse.json({ leads, count: leads.length });
}
