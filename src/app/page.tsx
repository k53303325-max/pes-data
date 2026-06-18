import { Header } from "@/components/landing/Header";
import { Hero } from "@/components/landing/Hero";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { Pricing } from "@/components/landing/Pricing";
import { Benefits } from "@/components/landing/Benefits";
import { ContactForm } from "@/components/landing/ContactForm";
import { Footer } from "@/components/landing/Footer";

export default function HomePage() {
  return (
    <>
      <Header />
      <main>
        <Hero />
        <HowItWorks />
        <Pricing />
        <Benefits />
        <ContactForm />
      </main>
      <Footer />
    </>
  );
}
