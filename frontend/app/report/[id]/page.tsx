import { notFound } from "next/navigation";
import { getReport } from "@/lib/api/reports";
import { IndustrySection } from "@/components/industry-section";
import { Navbar } from "@/components/navbar";
import { OriginalNewsCard } from "@/components/original-news-card";
import { ImpactedIndustriesGrid } from "@/components/impacted-industries-grid";
import { RecommendedStocksSidebar } from "@/components/recommended-stocks-sidebar";
import { ReportCTASection } from "@/components/report-cta-section";
import { FiShare2, FiBookmark } from "react-icons/fi";

interface ReportPageProps {
  params: Promise<{ id: string }>;
}

/**
 * 읽는 시간 계산 (200자당 1분)
 */
function calculateReadingTime(summary: string | null): number {
  if (!summary) return 0;
  return Math.max(1, Math.ceil(summary.length / 200));
}

/**
 * 보고서 상세 페이지
 */
export default async function ReportPage({ params }: ReportPageProps) {
  const { id } = await params;
  const reportId = parseInt(id, 10);

  if (isNaN(reportId)) {
    notFound();
  }

  let report;
  try {
    report = await getReport(reportId);
  } catch (error) {
    notFound();
  }

  const readingTime = calculateReadingTime(report.summary);
  const firstIndustry = report.industries.length > 0 ? report.industries[0] : null;
  const industryCategory = firstIndustry?.industry_name || "산업";

  return (
    <div className="min-h-screen bg-background">
      {/* Navbar */}
      <Navbar />

      {/* 메인 컨텐츠 */}
      <main className="pt-20">
        {/* 상단 바 */}
        <div className="container mx-auto px-4 py-4">
          <div className="max-w-6xl mx-auto flex items-center justify-between">
            <a href="/" className="text-muted-foreground hover:text-foreground transition-colors">
              ← 홈으로
            </a>
            <div className="flex items-center gap-4">
              <button className="p-2 hover:bg-muted rounded-lg transition-colors" aria-label="공유">
                <FiShare2 className="w-5 h-5 text-muted-foreground" />
              </button>
              <button className="p-2 hover:bg-muted rounded-lg transition-colors" aria-label="북마크">
                <FiBookmark className="w-5 h-5 text-muted-foreground" />
              </button>
            </div>
          </div>
        </div>

        {/* 헤더 섹션 */}
        <section className="container mx-auto px-4 py-8">
          <div className="max-w-6xl mx-auto">
            {/* 배지들 */}
            <div className="flex items-center gap-2 flex-wrap mb-4">
              <span className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-xs font-medium">
                {industryCategory}
              </span>
              <span className="text-sm text-muted-foreground">
                {new Date(report.analysis_date).toLocaleDateString("ko-KR", {
                  year: "numeric",
                  month: "2-digit",
                  day: "2-digit",
                })}{" "}
                · 읽는 시간 {readingTime}분
              </span>
            </div>

            {/* 제목 */}
            <h1 className="text-4xl md:text-5xl font-bold mb-6 text-foreground">{report.title}</h1>

            {/* 요약 */}
            {report.summary && <p className="text-lg text-muted-foreground leading-relaxed mb-8">{report.summary}</p>}
          </div>
        </section>

        {/* 2열 레이아웃 */}
        <section className="container mx-auto px-4 py-8">
          <div className="max-w-6xl mx-auto">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* 왼쪽 열: 메인 콘텐츠 */}
              <div className="lg:col-span-2">
                {/* 원본 뉴스 */}
                {report.news_articles.length > 0 && <OriginalNewsCard article={report.news_articles[0]} />}

                {/* 사회적 파급효과 분석 */}
                {report.industries.length > 0 && (
                  <div className="mb-8">
                    <div className="flex items-center gap-2 mb-6">
                      <svg
                        className="w-5 h-5 text-primary"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        xmlns="http://www.w3.org/2000/svg"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                        />
                      </svg>
                      <h2 className="text-xl font-semibold text-foreground">사회적 파급효과 분석</h2>
                    </div>
                    <div>
                      {report.industries.map((industry) => (
                        <IndustrySection key={industry.id} industry={industry} />
                      ))}
                    </div>
                  </div>
                )}

                {/* 영향받는 산업 */}
                {report.industries.length > 0 && <ImpactedIndustriesGrid industries={report.industries} />}
              </div>

              {/* 오른쪽 열: 추천 종목 사이드바 */}
              <div className="lg:col-span-1">
                {report.industries.length > 0 && <RecommendedStocksSidebar industries={report.industries} />}
              </div>
            </div>
          </div>
        </section>

        {/* CTA 섹션 */}
        <ReportCTASection />
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
