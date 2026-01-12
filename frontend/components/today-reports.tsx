import { Suspense } from "react";
import { getTodayReports } from "@/lib/api/reports";
import { ReportCard } from "./report-card";

/**
 * 로딩 스켈레톤 컴포넌트
 */
function ReportListSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="p-6 border rounded-lg animate-pulse bg-white dark:bg-slate-900">
          <div className="h-6 bg-slate-200 dark:bg-slate-700 rounded mb-2" />
          <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded mb-4 w-3/4" />
          <div className="flex gap-4">
            <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-16" />
            <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-16" />
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
  const reports = await getTodayReports();

  if (reports.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-slate-600 dark:text-slate-400">오늘 작성된 보고서가 없습니다.</p>
      </div>
    );
  }

  return (
    <div className="grid gap-6 md:grid-cols-2">
      {reports.slice(0, 4).map((report) => (
        <ReportCard key={report.id} report={report} />
      ))}
    </div>
  );
}

/**
 * 오늘의 보고서 목록 컴포넌트
 * Suspense로 감싸서 로딩 상태를 처리합니다.
 */
export function TodayReports() {
  return (
    <Suspense fallback={<ReportListSkeleton />}>
      <ReportList />
    </Suspense>
  );
}
