import { Stock } from "@/lib/api/reports";
import { FiTrendingUp, FiTrendingDown } from "react-icons/fi";

interface StockCardProps {
  stock: Stock;
}

/**
 * 주식 카드 컴포넌트
 * 이미지 디자인에 맞춘 레이아웃
 */
export function StockCard({ stock }: StockCardProps) {
  // 임시 목 데이터: 현재가, 변동률, 목표가
  const mockPrice = Math.floor(Math.random() * 200000) + 50000; // 50,000 ~ 250,000
  const mockChange = (Math.random() * 5 + 0.5).toFixed(1); // 0.5% ~ 5.5%
  const mockTargetPrice = Math.floor(mockPrice * 1.2); // 현재가의 120%
  const isPositive = stock.expected_trend === "up" || Math.random() > 0.3;

  const formatPrice = (price: number) => {
    return price.toLocaleString("ko-KR") + "원";
  };

  return (
    <div className="p-4 border rounded-lg bg-white hover:shadow-md transition-shadow mb-4">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h4 className="font-bold text-foreground mb-1">{stock.stock_name || "알 수 없음"}</h4>
          {stock.stock_code && <p className="text-sm text-muted-foreground">{stock.stock_code}</p>}
        </div>
        <div className="text-right">
          <div className="font-bold text-foreground mb-1">{formatPrice(mockPrice)}</div>
          <div
            className={`flex items-center gap-1 text-sm font-semibold ${
              isPositive ? "text-green-600" : "text-red-600"
            }`}
          >
            {isPositive ? <FiTrendingUp className="w-4 h-4" /> : <FiTrendingDown className="w-4 h-4" />}
            <span>
              {isPositive ? "+" : "-"}
              {mockChange}%
            </span>
          </div>
        </div>
      </div>
      {stock.reasoning && <p className="text-sm text-muted-foreground mb-3 leading-relaxed">{stock.reasoning}</p>}
      <div className="text-sm text-red-600 font-medium">목표가: {formatPrice(mockTargetPrice)}</div>
    </div>
  );
}
