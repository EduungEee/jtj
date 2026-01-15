import { Navbar } from "@/components/navbar";
import { HeroSection } from "@/components/hero-section";
import { RecentReportsSection } from "@/components/recent-reports-section";
import { HowItWorks } from "@/components/how-it-works";
import { CTASection } from "@/components/cta-section";
import { getNewsCount } from "@/lib/api/news";
import { getSubscriberCount } from "@/lib/api/subscribers";

// SSR 전용 - 정적 생성 비활성화
export const dynamic = "force-dynamic";

/**
 * 홈페이지 메인 컴포넌트
 */
export default async function Home() {
  // 뉴스 개수와 구독자 수를 병렬로 가져오기
  const [newsCount, subscriberCount] = await Promise.all([
    getNewsCount().catch((error) => {
      console.error("Failed to fetch news count:", error);
      return 0;
    }),
    getSubscriberCount().catch((error) => {
      console.error("Failed to fetch subscriber count:", error);
      return 0;
    }),
  ]);

  return (
    <div className="min-h-screen">
      {/* Navbar */}
      <Navbar />

      {/* 메인 컨텐츠 */}
      <main className="pt-16">
        {/* Hero 섹션 - 서비스 소개 */}
        <HeroSection newsCount={newsCount} subscriberCount={subscriberCount} />

        {/* 최신 보고서 섹션 */}
        <RecentReportsSection />

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
