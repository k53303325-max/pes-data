import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { z } from "zod";

const projectSchema = z.object({
  name: z.string().min(2),
  dailyLimit: z.number().min(1).default(100),
  clustersEnabled: z.boolean().default(false),
});

export async function GET() {
  const session = await getServerSession(authOptions);
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const projects = await prisma.project.findMany({
    where: { userId: session.user.id },
    include: {
      _count: { select: { leads: true, sources: true } },
    },
    orderBy: { createdAt: "desc" },
  });

  return NextResponse.json(projects);
}

export async function POST(req: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const body = await req.json();
    const data = projectSchema.parse(body);

    const project = await prisma.project.create({
      data: {
        userId: session.user.id,
        name: data.name,
        dailyLimit: data.dailyLimit,
        clustersEnabled: data.clustersEnabled,
      },
    });

    return NextResponse.json(project);
  } catch {
    return NextResponse.json({ error: "Invalid data" }, { status: 400 });
  }
}
