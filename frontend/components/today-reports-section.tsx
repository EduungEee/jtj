import { TodayReports } from "./today-reports";

/**
 * 오늘의 보고서 섹션 컴포넌트
 * 섹션 헤더와 보고서 목록을 포함
 */
export function TodayReportsSection() {
  return (
    <section id="today-reports" className="px-4 scroll-mt-16 py-20 bg-slate-50">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-3xl  font-bold mb-2 text-foreground">오늘의 분석 보고서</h2>
            <p className="text-muted-foreground">AI가 분석한 최신 뉴스 기반 주식 동향입니다</p>
          </div>
          <button className="hidden md:flex items-center gap-2 px-4 py-2 text-sm font-medium text-primary hover:text-primary/80 transition-colors">
            전체 보고서 보기
            <span>→</span>
          </button>
        </div>
        <TodayReports />
      </div>
    </section>
  );
}
