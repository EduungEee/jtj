import { Industry } from "@/lib/api/reports";
import { FiTrendingUp } from "react-icons/fi";
import { LiaIndustrySolid } from "react-icons/lia";

interface ImpactedIndustriesGridProps {
  industries: Industry[];
}

/**
 * 영향받는 산업 그리드 컴포넌트
 */
export function ImpactedIndustriesGrid({ industries }: ImpactedIndustriesGridProps) {
  if (industries.length === 0) {
    return null;
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <LiaIndustrySolid className="text-primary size-6 flex items-center justify-center" />
        <h2 className="text-xl font-semibold text-foreground">영향받는 산업</h2>
      </div>
      <div className="flex flex-col gap-3">
        {industries.map((industry) => (
          <div key={industry.id} className="p-4 bg-white rounded-lg border shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center gap-2 mb-2">
              <FiTrendingUp className="w-4 h-4 text-green-600" />
              <h3 className="font-semibold text-sm text-foreground">{industry.industry_name}</h3>
            </div>
            {industry.impact_description && (
              <p className="text-xs text-muted-foreground leading-relaxed">{industry.impact_description}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
