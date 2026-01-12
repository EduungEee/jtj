import { Industry } from "@/lib/api/reports";

interface IndustrySectionProps {
  industry: Industry;
}

/**
 * 산업별 분석 섹션 컴포넌트
 */
export function IndustrySection({ industry }: IndustrySectionProps) {
  const getImpactBadgeColor = (level: string | null) => {
    switch (level) {
      case "high":
        return "bg-red-100 text-red-700";
      case "medium":
        return "bg-gray-100 text-gray-700";
      case "low":
        return "bg-green-100 text-green-700";
      default:
        return "bg-muted text-muted-foreground";
    }
  };

  const getImpactText = (level: string | null) => {
    switch (level) {
      case "high":
        return "높은 영향";
      case "medium":
        return "중간 영향";
      case "low":
        return "낮은 영향";
      default:
        return "영향";
    }
  };

  return (
    <div className="p-6 bg-white rounded-lg border shadow-sm mb-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-bold text-foreground">{industry.industry_name}</h3>
        {industry.impact_level && (
          <span
            className={`px-3 py-1 rounded-full text-xs font-semibold ${getImpactBadgeColor(industry.impact_level)}`}
          >
            {getImpactText(industry.impact_level)}
          </span>
        )}
      </div>
      {industry.impact_description && (
        <p className="text-muted-foreground leading-relaxed">{industry.impact_description}</p>
      )}
    </div>
  );
}
