import { SiteNav } from "./components/layout/SiteNav";
import { AboutSection } from "./components/sections/AboutSection";
import { AiSection } from "./components/sections/AiSection";
import { DifferentiatorsSection } from "./components/sections/DifferentiatorsSection";
import { FeaturesSection } from "./components/sections/FeaturesSection";
import { FinalCtaSection } from "./components/sections/FinalCtaSection";
import { Footer } from "./components/sections/Footer";
import { HeroSection } from "./components/sections/HeroSection";
import { MethodologiesSection } from "./components/sections/MethodologiesSection";
import { OpenSourceSection } from "./components/sections/OpenSourceSection";
import { TemplatesSection } from "./components/sections/TemplatesSection";

export default function App() {
  return (
    <div className="min-h-screen bg-midnight">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-lg focus:bg-mint focus:px-4 focus:py-2 focus:text-midnight"
      >
        Skip to content
      </a>
      <SiteNav />
      <main id="main">
        <HeroSection />
        <AboutSection />
        <DifferentiatorsSection />
        <MethodologiesSection />
        <FeaturesSection />
        <AiSection />
        <TemplatesSection />
        <OpenSourceSection />
        <FinalCtaSection />
      </main>
      <Footer />
    </div>
  );
}
