import { Navbar } from "@/components/navbar";
import { HeroSection } from "@/components/hero-section";
import { TodayReportsSection } from "@/components/today-reports-section";
import { HowItWorks } from "@/components/how-it-works";
import { CTASection } from "@/components/cta-section";

/**
 * 홈페이지 메인 컴포넌트
 */
export default function Home() {
  return (
    <div className="min-h-screen">
      {/* Navbar */}
      <Navbar />

      {/* 메인 컨텐츠 */}
      <main className="pt-16">
        {/* Hero 섹션 - 서비스 소개 */}
        <HeroSection />

        {/* 오늘의 보고서 섹션 */}
        <TodayReportsSection />

        {/* 어떻게 작동하나요 섹션 */}
        <HowItWorks />

        {/* 지금 바로 시작하세요 섹션 */}
        <CTASection />
      </main>

      {/* 푸터 */}
      <footer className="border-t mt-12 bg-background">
        <div className="container mx-auto px-4 py-6 text-center text-muted-foreground">
          <p>© 2024 주식 동향 분석 서비스. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
