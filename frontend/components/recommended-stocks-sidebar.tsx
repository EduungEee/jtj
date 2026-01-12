import { Industry } from "@/lib/api/reports";
import { StockCard } from "./stock-card";

interface RecommendedStocksSidebarProps {
  industries: Industry[];
}

/**
 * 추천 종목 사이드바 컴포넌트
 */
export function RecommendedStocksSidebar({ industries }: RecommendedStocksSidebarProps) {
  // 모든 industries의 stocks를 모아서 중복 제거
  const allStocks = industries.flatMap((industry) => industry.stocks);
  const uniqueStocks = allStocks.filter((stock, index, self) => index === self.findIndex((s) => s.id === stock.id));

  if (uniqueStocks.length === 0) {
    return null;
  }

  return (
    <div className="sticky top-20">
      <div className="flex items-center gap-2 mb-4">
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
            d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
          />
        </svg>
        <h2 className="text-xl font-semibold text-foreground">추천 종목</h2>
      </div>
      <div>
        {uniqueStocks.map((stock) => (
          <StockCard key={stock.id} stock={stock} />
        ))}
      </div>
      <div className="mt-6 p-4 bg-muted rounded-lg">
        <p className="text-xs text-muted-foreground leading-relaxed">
          본 분석 보고서는 AI가 뉴스 데이터를 기반으로 작성한 것으로, 투자 권유가 아닙니다. 투자 결정은 본인의 판단과
          책임 하에 이루어져야 합니다.
        </p>
      </div>
    </div>
  );
}
