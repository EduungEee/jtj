import Link from "next/link";
import { ReportListItem } from "@/lib/api/reports";
import { FiTrendingUp, FiTrendingDown } from "react-icons/fi";
import { cn } from "@/lib/utils";

interface ReportCardProps {
  report: ReportListItem;
}

/**
 * 산업 카테고리별 색상 매핑
 */
function getCategoryColor(category: string | null): string {
  if (!category) return "bg-slate-100 text-slate-700";

  const categoryLower = category.toLowerCase();
  if (categoryLower.includes("반도체") || categoryLower.includes("2차전지")) {
    return "bg-green-100 text-green-700";
  }
  if (categoryLower.includes("금융")) {
    return "bg-orange-100 text-orange-700";
  }
  if (categoryLower.includes("게임")) {
    return "bg-red-100 text-red-700";
  }
  return "bg-slate-100 text-slate-700";
}

/**
 * 날짜 포맷팅
 */
function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, "0")}.${String(date.getDate()).padStart(
    2,
    "0",
  )}`;
}

/**
 * 보고서 카드 컴포넌트
 * 이미지 디자인에 맞춘 스타일
 */
export function ReportCard({ report }: ReportCardProps) {
  // 임시 데이터 (나중에 API에서 제공되면 제거)
  const mockCategory = report.industry_count > 0 ? "산업" : null;
  const mockTrend = "+1.5%"; // 임시 트렌드 값
  const mockCompanies = ["삼성전자", "SK하이닉스"]; // 임시 기업 목록
  const isPositive = mockTrend.startsWith("+");

  return (
    <Link
      href={`/report/${report.id}`}
      className="block relative p-6 border rounded-lg hover:shadow-lg transition-all bg-white group"
    >
      {/* 날짜 - 우측 상단 */}
      <div className="absolute top-4 right-4 text-xs text-muted-foreground">{formatDate(report.analysis_date)}</div>

      {/* 카테고리 태그 */}
      {mockCategory && (
        <div
          className={cn("inline-block px-3 py-1 rounded-full text-xs font-medium mb-4", getCategoryColor(mockCategory))}
        >
          {mockCategory}
        </div>
      )}

      {/* 제목 */}
      <h3 className="font-bold text-lg mb-3 text-card-foreground pr-16">{report.title}</h3>

      {/* 설명 */}
      {report.summary && (
        <p className="text-sm text-muted-foreground mb-4 line-clamp-3 leading-relaxed">{report.summary}</p>
      )}

      {/* 관련 기업들 */}
      {mockCompanies.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {mockCompanies.map((company, index) => (
            <span key={index} className="text-xs text-muted-foreground">
              {company}
            </span>
          ))}
        </div>
      )}

      {/* 트렌드 */}
      <div
        className={cn("flex items-center gap-1 text-sm font-semibold", isPositive ? "text-green-600" : "text-red-600")}
      >
        {isPositive ? <FiTrendingUp className="w-4 h-4" /> : <FiTrendingDown className="w-4 h-4" />}
        <span>{mockTrend}</span>
      </div>
    </Link>
  );
}
