/**
 * 보고서 API 클라이언트
 * FastAPI 백엔드와 통신하는 함수들
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * 뉴스 기사 타입
 */
export interface NewsArticle {
  id: number;
  title: string;
  content: string | null;
  source: string | null;
  url: string | null;
  published_at: string | null;
}

/**
 * 주식 분석 타입
 */
export interface Stock {
  id: number;
  stock_code: string | null;
  stock_name: string | null;
  expected_trend: string | null;
  confidence_score: number | null;
  reasoning: string | null;
}

/**
 * 산업 분석 타입
 */
export interface Industry {
  id: number;
  industry_name: string;
  impact_level: string | null;
  impact_description: string | null;
  trend_direction: string | null;
  stocks: Stock[];
}

/**
 * 보고서 상세 타입
 */
export interface ReportDetail {
  id: number;
  title: string;
  summary: string | null;
  analysis_date: string;
  created_at: string;
  news_articles: NewsArticle[];
  industries: Industry[];
}

/**
 * 보고서 목록 항목 타입
 */
export interface ReportListItem {
  id: number;
  title: string;
  summary: string | null;
  analysis_date: string;
  created_at: string;
  news_count: number;
  industry_count: number;
}

/**
 * API 에러 타입
 */
export class ApiError extends Error {
  constructor(message: string, public statusCode: number, public response?: unknown) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * 전체 보고서 목록을 조회합니다 (최신순).
 */
export async function getAllReports(limit: number = 10): Promise<ReportListItem[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/reports?limit=${limit}`, {
      next: { revalidate: 60 }, // 60초마다 재검증
    });

    if (!response.ok) {
      throw new ApiError(`Failed to fetch reports: ${response.statusText}`, response.status);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(`Network error: ${error instanceof Error ? error.message : "Unknown error"}`, 0);
  }
}

/**
 * 오늘의 보고서 목록을 조회합니다.
 */
export async function getTodayReports(): Promise<ReportListItem[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/reports/today`, {
      next: { revalidate: 60 }, // 60초마다 재검증
    });

    if (!response.ok) {
      throw new ApiError(`Failed to fetch today's reports: ${response.statusText}`, response.status);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(`Network error: ${error instanceof Error ? error.message : "Unknown error"}`, 0);
  }
}

/**
 * 보고서 상세 정보를 조회합니다.
 */
export async function getReport(reportId: number): Promise<ReportDetail> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/report/${reportId}`, {
      next: { revalidate: 300 }, // 5분마다 재검증
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw new ApiError("보고서를 찾을 수 없습니다.", 404);
      }
      throw new ApiError(`Failed to fetch report: ${response.statusText}`, response.status);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(`Network error: ${error instanceof Error ? error.message : "Unknown error"}`, 0);
  }
}
