import { FiFileText, FiZap, FiFile, FiMail } from "react-icons/fi";

/**
 * 어떻게 작동하나요 섹션 컴포넌트
 * 4단계 프로세스를 2x2 그리드로 표시
 * 이미지 디자인과 정확히 일치
 */
export function HowItWorks() {
  return (
    <section id="features" className="container mx-auto px-4 py-16 scroll-mt-20">
      <div className="max-w-4xl mx-auto text-center mb-12">
        <h2 className="text-4xl md:text-5xl font-bold mb-4 text-foreground">어떻게 작동하나요?</h2>
        <p className="text-lg text-muted-foreground">AI가 뉴스를 분석하여 투자 인사이트를 제공하는 4단계 프로세스</p>
      </div>

      {/* 2x2 그리드 - 하나의 큰 둥근 컨테이너 */}
      <div className="max-w-4xl mx-auto">
        <div className="grid md:grid-cols-2 gap-0 rounded-xl overflow-hidden bg-card">
          {/* Step 1: 뉴스 수집 */}
          <div className="p-4 md:p-8 md:border-r border-border bg-background">
            <div className="flex items-start gap-4">
              <div className="shrink-0">
                <div className="w-14 h-14 bg-primary/10 rounded-xl flex items-center justify-center">
                  <FiFileText className="w-7 h-7 text-primary" />
                </div>
              </div>
              <div className="flex-1">
                <div className="text-sm font-medium text-primary mb-2">Step 1</div>
                <h3 className="text-xl font-bold mb-3 text-foreground">뉴스 수집</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  네이버 뉴스 API를 통해 경제, 산업, 기업 관련 최신 뉴스를 실시간으로 수집합니다.
                </p>
              </div>
            </div>
          </div>

          {/* Step 2: AI 분석 */}
          <div className="p-4 md:p-8 border-border bg-background">
            <div className="flex items-start gap-4 md:flex-row-reverse">
              <div className="shrink-0">
                <div className="w-14 h-14 bg-primary/10 rounded-xl flex items-center justify-center">
                  <FiZap className="w-7 h-7 text-primary" />
                </div>
              </div>
              <div className="flex-1 md:text-right">
                <div className="text-sm font-medium text-primary mb-2">Step 2</div>
                <h3 className="text-xl font-bold mb-3 text-foreground">AI 분석</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  GPT-4 기반 AI가 뉴스의 사회적 파급효과를 예측하고, 영향받는 산업과 주식을 분석합니다.
                </p>
              </div>
            </div>
          </div>

          {/* Step 3: 보고서 생성 */}
          <div className="p-4 md:p-8 md:border-r border-border bg-background">
            <div className="flex items-start gap-4">
              <div className="shrink-0">
                <div className="w-14 h-14 bg-primary/10 rounded-xl flex items-center justify-center">
                  <FiFile className="w-7 h-7 text-primary" />
                </div>
              </div>
              <div className="flex-1">
                <div className="text-sm font-medium text-primary mb-2">Step 3</div>
                <h3 className="text-xl font-bold mb-3 text-foreground">보고서 생성</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  분석 결과를 바탕으로 이해하기 쉬운 형태의 투자 인사이트 보고서를 자동 생성합니다.
                </p>
              </div>
            </div>
          </div>

          {/* Step 4: 이메일 전송 */}
          <div className="p-4 md:p-8 bg-background">
            <div className="flex items-start gap-4 md:flex-row-reverse">
              <div className="shrink-0">
                <div className="w-14 h-14 bg-primary/10 rounded-xl flex items-center justify-center">
                  <FiMail className="w-7 h-7 text-primary" />
                </div>
              </div>
              <div className="flex-1 md:text-right">
                <div className="text-sm font-medium text-primary mb-2">Step 4</div>
                <h3 className="text-xl font-bold mb-3 text-foreground">이메일 전송</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  매일 아침, 구독자에게 맞춤형 분석 보고서 링크를 이메일로 전송합니다.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
