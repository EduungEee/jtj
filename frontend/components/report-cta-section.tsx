import { FiArrowRight } from "react-icons/fi";

/**
 * 보고서 페이지용 CTA 섹션
 */
export function ReportCTASection() {
  return (
    <section className="py-16" style={{ backgroundColor: "#FFF0ED" }}>
      <div className="container mx-auto px-4">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-4 text-foreground">매일 아침 분석 보고서를 받아보세요</h2>
          <p className="text-lg text-muted-foreground mb-8">AI가 분석한 최신 주식 동향을 이메일로 전달해 드립니다</p>
          <button className="inline-flex items-center gap-2 px-8 py-4 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-lg font-semibold">
            <span>무료로 시작하기</span>
            <FiArrowRight className="w-5 h-5" />
          </button>
        </div>
      </div>
    </section>
  );
}
