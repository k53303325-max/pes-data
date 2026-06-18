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
  const status = searchParams.get("status");
  const cluster = searchParams.get("cluster");
  const source = searchParams.get("source");
  const page = parseInt(searchParams.get("page") || "1");
  const limit = parseInt(searchParams.get("limit") || "20");
  const skip = (page - 1) * limit;

  const where: Record<string, unknown> = {};

  if (projectId) {
    const project = await prisma.project.findFirst({
      where: { id: projectId, userId: session.user.id },
    });
    if (!project) {
      return NextResponse.json({ error: "Project not found" }, { status: 404 });
    }
    where.projectId = projectId;
  } else {
    const projects = await prisma.project.findMany({
      where: { userId: session.user.id },
      select: { id: true },
    });
    where.projectId = { in: projects.map((p) => p.id) };
  }

  if (status) where.status = status;
  if (cluster) where.cluster = cluster;
  if (source) where.source = { contains: source, mode: "insensitive" };

  const [leads, total] = await Promise.all([
    prisma.lead.findMany({
      where,
      orderBy: { createdAt: "desc" },
      skip,
      take: limit,
    }),
    prisma.lead.count({ where }),
  ]);

  return NextResponse.json({
    leads,
    pagination: {
      page,
      limit,
      total,
      totalPages: Math.ceil(total / limit),
    },
  });
}

export async function PATCH(req: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { id, status } = await req.json();

  const lead = await prisma.lead.findUnique({
    where: { id },
    include: { projectRef: true },
  });

  if (!lead || lead.projectRef.userId !== session.user.id) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  const updated = await prisma.lead.update({
    where: { id },
    data: { status },
  });

  return NextResponse.json(updated);
}
