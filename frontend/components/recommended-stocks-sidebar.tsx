import { Industry } from "@/lib/api/reports";
import { StockCard } from "./stock-card";
import { BsBarChart } from "react-icons/bs";

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
        <BsBarChart className="text-primary size-5 flex items-center justify-center" />
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
