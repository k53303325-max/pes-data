import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { z } from "zod";

const leadWebhookSchema = z.object({
  projectId: z.string(),
  phone: z.string(),
  source: z.string(),
  cluster: z.enum(["MAIN", "CLUSTER_1", "CLUSTER_2", "CLUSTER_3"]).optional(),
  secret: z.string().optional(),
});

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const data = leadWebhookSchema.parse(body);

    const project = await prisma.project.findUnique({
      where: { id: data.projectId },
      include: { user: true },
    });

    if (!project || !project.active) {
      return NextResponse.json({ error: "Project not found" }, { status: 404 });
    }

    if (project.user.balance <= 0) {
      return NextResponse.json({ error: "Insufficient balance" }, { status: 402 });
    }

    const sourceRecord = await prisma.source.findFirst({
      where: { projectId: data.projectId, domain: data.source },
    });

    const lead = await prisma.lead.create({
      data: {
        projectId: data.projectId,
        sourceId: sourceRecord?.id,
        phone: data.phone,
        source: data.source,
        cluster: data.cluster || "MAIN",
      },
    });

    await prisma.user.update({
      where: { id: project.userId },
      data: { balance: { decrement: 1 } },
    });

    await prisma.transaction.create({
      data: {
        userId: project.userId,
        amount: -1,
        type: "CHARGE",
        description: `Лид ${data.phone} из ${data.source}`,
      },
    });

    const webhooks = await prisma.webhook.findMany({
      where: { userId: project.userId, active: true },
    });

    for (const webhook of webhooks) {
      fetch(webhook.url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ event: "lead.created", lead }),
      }).catch(() => {});
    }

    return NextResponse.json({ success: true, lead });
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ error: "Invalid payload" }, { status: 400 });
    }
    return NextResponse.json({ error: "Server error" }, { status: 500 });
  }
}
