import { PrismaClient, Plan, UserRole, LeadStatus, Cluster } from "@prisma/client";
import bcrypt from "bcryptjs";

const prisma = new PrismaClient();

async function main() {
  const adminPassword = await bcrypt.hash("admin123", 10);
  const userPassword = await bcrypt.hash("demo123", 10);

  const admin = await prisma.user.upsert({
    where: { email: "admin@pesdata.ru" },
    update: {},
    create: {
      email: "admin@pesdata.ru",
      name: "Администратор",
      phone: "+79001234567",
      password: adminPassword,
      role: UserRole.ADMIN,
      plan: Plan.MAX,
      balance: 100000,
    },
  });

  const demoUser = await prisma.user.upsert({
    where: { email: "demo@pesdata.ru" },
    update: {},
    create: {
      email: "demo@pesdata.ru",
      name: "Демо Клиент",
      phone: "+79007654321",
      password: userPassword,
      role: UserRole.USER,
      plan: Plan.START,
      balance: 2500,
    },
  });

  const project = await prisma.project.upsert({
    where: { id: "demo-project-1" },
    update: {},
    create: {
      id: "demo-project-1",
      userId: demoUser.id,
      name: "Основной проект",
      dailyLimit: 200,
      active: true,
      clustersEnabled: true,
    },
  });

  const source1 = await prisma.source.create({
    data: {
      projectId: project.id,
      domain: "competitor-shop.ru",
      active: true,
      conversionRate: 12.5,
    },
  });

  const source2 = await prisma.source.create({
    data: {
      projectId: project.id,
      domain: "rival-market.com",
      active: true,
      conversionRate: 8.3,
    },
  });

  const phones = [
    "+79001112233",
    "+79002223344",
    "+79003334455",
    "+79004445566",
    "+79005556677",
    "+79006667788",
    "+79007778899",
    "+79008889900",
  ];

  const clusters = [Cluster.MAIN, Cluster.CLUSTER_1, Cluster.CLUSTER_2, Cluster.CLUSTER_3];
  const statuses = [LeadStatus.NEW, LeadStatus.CONTACTED, LeadStatus.SUCCESS, LeadStatus.FAILED];

  for (let i = 0; i < phones.length; i++) {
    const daysAgo = Math.floor(Math.random() * 30);
    const createdAt = new Date();
    createdAt.setDate(createdAt.getDate() - daysAgo);

    await prisma.lead.create({
      data: {
        projectId: project.id,
        sourceId: i % 2 === 0 ? source1.id : source2.id,
        phone: phones[i],
        source: i % 2 === 0 ? source1.domain : source2.domain,
        cluster: clusters[i % clusters.length],
        status: statuses[i % statuses.length],
        createdAt,
      },
    });
  }

  await prisma.transaction.createMany({
    data: [
      {
        userId: demoUser.id,
        amount: 5000,
        type: "DEPOSIT",
        description: "Пополнение баланса",
      },
      {
        userId: demoUser.id,
        amount: -800,
        type: "CHARGE",
        description: "Списание за лиды",
      },
    ],
  });

  await prisma.apiKey.create({
    data: {
      userId: demoUser.id,
      key: "pk_demo_" + Math.random().toString(36).slice(2, 18),
    },
  });

  await prisma.webhook.create({
    data: {
      userId: demoUser.id,
      url: "https://example.com/webhook/leads",
      active: true,
    },
  });

  await prisma.platformStats.upsert({
    where: { id: "platform" },
    update: { totalLeads: 8, totalUsers: 2, totalProjects: 1 },
    create: { id: "platform", totalLeads: 8, totalUsers: 2, totalProjects: 1 },
  });

  console.log("Seed completed:", { admin: admin.email, demo: demoUser.email });
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
