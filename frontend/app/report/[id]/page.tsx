import { notFound } from "next/navigation";
import { auth } from "@clerk/nextjs/server";
import { getReport } from "@/lib/api/reports";
import { IndustrySection } from "@/components/industry-section";
import { Navbar } from "@/components/navbar";
import { ImpactedIndustriesGrid } from "@/components/impacted-industries-grid";
import { ReportCTASection } from "@/components/report-cta-section";
import { ShareButton } from "@/components/share-button";

interface ReportPageProps {
  params: Promise<{ id: string }>;
}

// SSR 전용 - 정적 생성 비활성화
export const dynamic = "force-dynamic";

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

  // 로그인 상태 확인
  const { userId } = await auth();
  const isSignedIn = !!userId;

  const readingTime = calculateReadingTime(report.summary);
  const firstIndustry = report.industries.length > 0 ? report.industries[0] : null;
  const industryCategory = firstIndustry?.industry_name || "산업";

  return (
    <div className="min-h-screen bg-background">
      {/* Navbar */}
      <Navbar />

      {/* 메인 컨텐츠 */}
      <main className="mt-20 sm:mt-30 max-w-6xl mx-auto">
        <div className="container mx-auto px-4">
          <div className="flex flex-col lg:flex-row gap-8">
            {/* 왼쪽: 모든 콘텐츠 */}
            <div className="flex-1 min-w-0">
              {/* 상단 바 */}
              <div className="py-4">
                <div className="max-w-6xl mx-auto flex items-center justify-between">
                  <a href="/" className="text-muted-foreground hover:text-foreground transition-colors">
                    ← 홈으로
                  </a>
                  <div className="flex items-center gap-4 relative">
                    <ShareButton title={report.title} reportId={reportId} />
                  </div>
                </div>
              </div>

              {/* 헤더 섹션 */}
              <section className="py-8">
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
                  {report.summary && (
                    <div className="my-10">
                      <div
                        className="text-lg text-muted-foreground leading-relaxed prose prose-lg max-w-none"
                        dangerouslySetInnerHTML={{
                          __html: (() => {
                            // 이미 <p> 태그가 포함되어 있는지 확인
                            if (report.summary.includes("<p>")) {
                              return report.summary;
                            }
                            // <p> 태그가 없으면 문단별로 분리
                            return report.summary
                              .split(/\n\n+/)
                              .filter((part) => part.trim())
                              .map((part) => `<p>${part.trim()}</p>`)
                              .join("");
                          })(),
                        }}
                      />
                    </div>
                  )}
                </div>
              </section>

              {/* 메인 콘텐츠 섹션 */}
              <section className="py-8 relative">
                <div className="max-w-6xl mx-auto">
                  {/* 사회적 파급효과 분석 */}
                  {report.industries.length > 0 && (
                    <div className="mb-8">
                      {/* 제목 - 항상 선명하게 표시 */}
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
                      {/* 콘텐츠 */}
                      <div className="relative">
                        {isSignedIn ? (
                          // 로그인한 경우: 실제 콘텐츠 표시
                          report.industries.map((industry) => <IndustrySection key={industry.id} industry={industry} />)
                        ) : (
                          // 로그인하지 않은 경우: 플레이스홀더 콘텐츠 표시 (흐리게)
                          <div className="blur-sm opacity-70">
                            <div className="p-6 bg-white rounded-lg border shadow-sm mb-4">
                              <div className="flex items-center justify-between mb-4">
                                <h3 className="text-xl font-bold text-foreground">분석 중인 산업</h3>
                                <span className="px-3 py-1 rounded-full text-xs font-semibold bg-gray-100 text-gray-700">
                                  분석 중
                                </span>
                              </div>
                              <p className="text-muted-foreground leading-relaxed">
                                로그인하시면 상세한 산업별 분석 내용을 확인하실 수 있습니다. AI가 최신 뉴스를 기반으로
                                사회적 파급효과를 분석하고, 영향받는 산업과 주식을 추천해드립니다.
                              </p>
                            </div>
                            <div className="p-6 bg-white rounded-lg border shadow-sm mb-4">
                              <div className="flex items-center justify-between mb-4">
                                <h3 className="text-xl font-bold text-foreground">추가 분석 진행 중</h3>
                                <span className="px-3 py-1 rounded-full text-xs font-semibold bg-gray-100 text-gray-700">
                                  분석 중
                                </span>
                              </div>
                              <p className="text-muted-foreground leading-relaxed">
                                매일 아침 업데이트되는 분석 보고서를 이메일로 받아보세요. 투자 결정에 도움이 되는
                                인사이트를 제공합니다.
                              </p>
                            </div>
                            <div className="p-6 bg-white rounded-lg border shadow-sm mb-4">
                              <div className="flex items-center justify-between mb-4">
                                <h3 className="text-xl font-bold text-foreground">심층 분석 데이터</h3>
                                <span className="px-3 py-1 rounded-full text-xs font-semibold bg-gray-100 text-gray-700">
                                  분석 중
                                </span>
                              </div>
                              <p className="text-muted-foreground leading-relaxed">
                                로그인하시면 더 많은 산업 분석과 추천 종목 정보를 확인하실 수 있습니다.
                              </p>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* CTA 오버레이 (로그인하지 않은 경우에만 표시) */}
                {!isSignedIn && (
                  <div className="absolute inset-0 flex items-center justify-center z-10">
                    <div className="bg-white/95 backdrop-blur-sm rounded-lg shadow-2xl p-6 w-full max-w-xl mx-4">
                      <ReportCTASection />
                    </div>
                  </div>
                )}
              </section>
            </div>

            {/* 오른쪽: 영향받는 산업 사이드바 (모바일에서는 위로) */}
            <div className="lg:w-80 lg:shrink-0">
              <div className="lg:sticky lg:top-24">
                {report.industries.length > 0 && <ImpactedIndustriesGrid industries={report.industries} />}
              </div>
            </div>
          </div>
        </div>
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
