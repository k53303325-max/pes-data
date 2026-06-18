import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { z } from "zod";

const applicationSchema = z.object({
  name: z.string().min(2),
  phone: z.string().min(10),
  email: z.string().email(),
  company: z.string().optional(),
  message: z.string().optional(),
});

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const data = applicationSchema.parse(body);

    const application = await prisma.application.create({
      data,
    });

    return NextResponse.json({ success: true, id: application.id });
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ error: "Неверные данные" }, { status: 400 });
    }
    return NextResponse.json({ error: "Ошибка сервера" }, { status: 500 });
  }
}

export async function GET() {
  const session = await getServerSession(authOptions);
  if (!session || session.user.role !== "ADMIN") {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const applications = await prisma.application.findMany({
    orderBy: { createdAt: "desc" },
    take: 50,
  });

  return NextResponse.json(applications);
}
