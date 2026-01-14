import { Suspense } from "react";
import { getAllReports } from "@/lib/api/reports";
import { ReportCard } from "./report-card";

/**
 * 로딩 스켈레톤 컴포넌트
 */
function ReportListSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {[1, 2, 3, 4, 5, 6].map((i) => (
        <div key={i} className="p-6 border rounded-lg animate-pulse bg-white">
          <div className="h-6 bg-slate-200 rounded mb-2" />
          <div className="h-4 bg-slate-200 rounded mb-4 w-3/4" />
          <div className="flex gap-4">
            <div className="h-3 bg-slate-200 rounded w-16" />
            <div className="h-3 bg-slate-200 rounded w-16" />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * 보고서 목록 컴포넌트 (Server Component)
 */
async function ReportList() {
  const reports = await getAllReports(10);

  if (reports.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-slate-600">작성된 보고서가 없습니다.</p>
      </div>
    );
  }

  return (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      {reports.map((report) => (
        <ReportCard key={report.id} report={report} />
      ))}
    </div>
  );
}

/**
 * 최신 보고서 목록 컴포넌트
 * Suspense로 감싸서 로딩 상태를 처리합니다.
 */
export function RecentReports() {
  return (
    <Suspense fallback={<ReportListSkeleton />}>
      <ReportList />
    </Suspense>
  );
}
