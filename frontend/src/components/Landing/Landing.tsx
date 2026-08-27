import { LandingNavbar } from './LandingNavbar';
import { HeroSection } from './HeroSection';
import { InstitutionCorpusBar } from './InstitutionCorpusBar';
import { ValueProposition } from './ValueProposition';
import { SpecializationGrid } from './SpecializationGrid';
import { SecuritySection } from './SecuritySection';
import { PricingSection } from './PricingSection';
import { FAQSection } from './FAQSection';
import { LandingFooter } from './LandingFooter';
import './Landing.css';

interface LandingProps {
  onGoToApp: () => void;
  onLogin: () => void;
}

export function Landing({ onGoToApp, onLogin }: LandingProps) {
  return (
    <div className="landing-page">
      {/* 1. Navbar */}
      <LandingNavbar onGoToApp={onGoToApp} onLogin={onLogin} />

      {/* 2. Hero with Interactive Legal Simulator */}
      <HeroSection onGoToApp={onGoToApp} />

      {/* 3. Official High Court Corpus Bar */}
      <InstitutionCorpusBar />

      {/* 4. Value Proposition */}
      <ValueProposition />

      {/* 5. Specializations Matrix */}
      <SpecializationGrid />

      {/* 6. Security & Legal Confidentiality */}
      <SecuritySection />

      {/* 7. Pricing & Subscriptions in COP */}
      <PricingSection onGoToApp={onGoToApp} />

      {/* 8. FAQ Accordion */}
      <FAQSection />

      {/* 9. Final CTA & Footer */}
      <LandingFooter onGoToApp={onGoToApp} />
    </div>
  );
}
