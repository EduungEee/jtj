import Link from "next/link";
import { ReportListItem } from "@/lib/api/reports";
import { cn } from "@/lib/utils";
import { FiFileText, FiCalendar, FiBarChart2 } from "react-icons/fi";

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
 * HTML 태그 제거 (summary에서 <p> 태그 등 제거)
 */
function stripHtmlTags(html: string | null): string {
  if (!html) return "";
  return html.replace(/<[^>]*>/g, "").trim();
}

/**
 * 보고서 카드 컴포넌트
 * 이미지 디자인에 맞춘 스타일
 */
export function ReportCard({ report }: ReportCardProps) {
  // metadata에서 산업군 정보 추출
  const industries = report.report_metadata?.industries || [];
  const industryNames = industries.map((ind) => ind.industry_name).filter(Boolean);
  
  // 첫 번째 산업군을 카테고리로 사용 (없으면 기본값)
  const category = industryNames.length > 0 ? industryNames[0] : (report.industry_count > 0 ? "산업" : null);

  return (
    <Link
      href={`/report/${report.id}`}
      className="block relative bg-white border-l-4 border-l-primary rounded-lg shadow-sm hover:shadow-md transition-all group overflow-hidden"
    >
      {/* 왼쪽 색상 바 배경 */}
      <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-primary to-primary/60" />

      <div className="p-6 pl-8">
        {/* 헤더: 아이콘과 날짜 */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <FiFileText className="w-5 h-5 text-primary" />
            </div>
            <div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                <FiCalendar className="w-3 h-3" />
                <span>{formatDate(report.analysis_date)}</span>
              </div>
              {report.industry_count > 0 && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <FiBarChart2 className="w-3 h-3" />
                  <span>{report.industry_count}개 산업 분석</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 제목 */}
        <h3 className="font-bold text-xl mb-3 text-foreground group-hover:text-primary transition-colors line-clamp-2">
          {report.title}
        </h3>

        {/* 설명 */}
        {report.summary && (
          <p className="text-sm text-muted-foreground mb-4 line-clamp-3 leading-relaxed">
            {stripHtmlTags(report.summary)}
          </p>
        )}

        {/* 산업군 태그들 */}
        {industryNames.length > 0 && (
          <div className="flex items-center gap-2 mt-4 pt-4 border-t flex-wrap">
            {industryNames.slice(0, 3).map((industryName, index) => (
              <div
                key={index}
                className={cn("inline-block px-3 py-1 rounded-md text-xs font-medium", getCategoryColor(industryName))}
              >
                {industryName}
              </div>
            ))}
            {industryNames.length > 3 && (
              <span className="text-xs text-muted-foreground">+{industryNames.length - 3}</span>
            )}
          </div>
        )}

        {/* 읽기 더보기 힌트 */}
        <div className="mt-4 pt-4 border-t flex items-center gap-2 text-xs text-primary">
          <span>보고서 보기</span>
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </div>
      </div>
    </Link>
  );
}
