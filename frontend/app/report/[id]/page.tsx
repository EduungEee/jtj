import { notFound } from "next/navigation";
import { getReport } from "@/lib/api/reports";
import { IndustrySection } from "@/components/industry-section";
import { Navbar } from "@/components/navbar";
import { ImpactedIndustriesGrid } from "@/components/impacted-industries-grid";
import { RecommendedStocksSidebar } from "@/components/recommended-stocks-sidebar";
import { ReportCTASection } from "@/components/report-cta-section";
import { FiShare2, FiBookmark, FiExternalLink } from "react-icons/fi";

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
      <main className="mt-20 sm:mt-30">
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
            <div className="my-10">
              <p className="text-lg text-muted-foreground leading-relaxed mb-4">
                {/* 더미데이터로 UI 보여주기 */}
                {"그러므로 우리는 이러한 상황에서 중요한 결정을 내려야 합니다. 또한 이러한 문제들은 복잡한 관계를 가지고 있으며, 서로 영향을 미치고 있습니다. 그러나 우리는 이러한 어려움을 극복할 수 있는 방법을 찾아야 합니다. 그리고 이러한 노력은 결국 좋은 결과를 가져다 줄 것입니다. 그러므로 우리는 계속해서 노력해야 하며, 포기하지 말아야 합니다. 또한 이러한 과정에서 우리는 많은 것을 배울 수 있으며, 성장할 수 있습니다. 그러나 때로는 실패할 수도 있지만, 그것도 우리에게는 중요한 경험이 될 것입니다. 그리고 이러한 경험들은 우리를 더욱 강하게 만들어 줄 것입니다. 그러므로 우리는 두려워하지 말고 앞으로 나아가야 합니다. 또한 우리는 서로 협력하며 함께 나아가야 하며, 혼자서는 해결할 수 없는 문제들도 함께하면 해결할 수 있습니다. 그러나 때로는 혼자서 생각할 시간도 필요하며, 그 시간을 통해 우리는 더 깊이 있는 통찰을 얻을 수 있습니다. 그리고 이러한 통찰은 우리의 결정을 더욱 명확하게 만들어 줄 것입니다. 그러므로 우리는 항상 열린 마음으로 새로운 아이디어를 받아들여야 하며, 변화에 적응할 수 있는 유연성을 가져야 합니다." ||
                  report.summary}
              </p>
              <p className="text-lg text-muted-foreground leading-relaxed mb-4">
                {/* 더미데이터로 UI 보여주기 */}
                {"그러므로 우리는 이러한 상황에서 중요한 결정을 내려야 합니다. 또한 이러한 문제들은 복잡한 관계를 가지고 있으며, 서로 영향을 미치고 있습니다. 그러나 우리는 이러한 어려움을 극복할 수 있는 방법을 찾아야 합니다. 그리고 이러한 노력은 결국 좋은 결과를 가져다 줄 것입니다. 그러므로 우리는 계속해서 노력해야 하며, 포기하지 말아야 합니다. 또한 이러한 과정에서 우리는 많은 것을 배울 수 있으며, 성장할 수 있습니다. 그러나 때로는 실패할 수도 있지만, 그것도 우리에게는 중요한 경험이 될 것입니다. 그리고 이러한 경험들은 우리를 더욱 강하게 만들어 줄 것입니다. 그러므로 우리는 두려워하지 말고 앞으로 나아가야 합니다. 또한 우리는 서로 협력하며 함께 나아가야 하며, 혼자서는 해결할 수 없는 문제들도 함께하면 해결할 수 있습니다. 그러나 때로는 혼자서 생각할 시간도 필요하며, 그 시간을 통해 우리는 더 깊이 있는 통찰을 얻을 수 있습니다. 그리고 이러한 통찰은 우리의 결정을 더욱 명확하게 만들어 줄 것입니다. 그러므로 우리는 항상 열린 마음으로 새로운 아이디어를 받아들여야 하며, 변화에 적응할 수 있는 유연성을 가져야 합니다." ||
                  report.summary}
              </p>
            </div>

            {/* 참고 뉴스 링크 */}
            {report.news_articles.length > 0 && (
              <div className="mb-8">
                <p className="text-xs text-muted-foreground mb-3">참고 뉴스:</p>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                  {report.news_articles.map((article) => (
                    <div key={article.id} className="min-w-0">
                      {article.url ? (
                        <a
                          href={article.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-primary/80 hover:text-primary hover:underline inline-flex items-center gap-1 w-full"
                        >
                          <span className="truncate">{article.title}</span>
                          <FiExternalLink className="w-3 h-3 shrink-0" />
                        </a>
                      ) : (
                        <span className="text-xs text-primary/70 truncate block">{article.title}</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>

        {/* 2열 레이아웃 */}
        <section className="container mx-auto px-4 py-8">
          <div className="max-w-6xl mx-auto">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* 왼쪽 열: 메인 콘텐츠 */}
              <div className="lg:col-span-2">
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
