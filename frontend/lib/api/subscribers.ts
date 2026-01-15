/**
 * 구독자 API 클라이언트
 * FastAPI 백엔드와 통신하는 함수들
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
 * 활성 구독자 수를 조회합니다.
 */
export async function getSubscriberCount(): Promise<number> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/subscribers/count`, {
      cache: "no-store", // 캐싱 비활성화
    });

    if (!response.ok) {
      throw new ApiError(`Failed to fetch subscriber count: ${response.statusText}`, response.status);
    }

    const data = await response.json();
    return data.count || 0;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    // 에러 발생 시 기본값 반환
    console.error("Failed to fetch subscriber count:", error);
    return 0;
  }
}
