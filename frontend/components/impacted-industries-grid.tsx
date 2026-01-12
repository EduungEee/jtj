import { Industry } from "@/lib/api/reports";
import { FiTrendingUp } from "react-icons/fi";

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
    <div className="mb-8">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-5 h-5 flex items-center justify-center">
          <svg
            className="w-5 h-5 text-orange-500"
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
        </div>
        <h2 className="text-xl font-semibold text-foreground">영향받는 산업</h2>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {industries.map((industry) => (
          <div key={industry.id} className="p-4 bg-white rounded-lg border shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center gap-2 mb-2">
              <FiTrendingUp className="w-4 h-4 text-green-600" />
              <h3 className="font-semibold text-sm text-foreground">{industry.industry_name}</h3>
            </div>
            {industry.impact_description && (
              <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
                {industry.impact_description}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
