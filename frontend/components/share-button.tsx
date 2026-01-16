"use client";

import { useState, useEffect } from "react";
import { FiShare2, FiCheck } from "react-icons/fi";

interface ShareButtonProps {
  title: string;
  reportId: number;
}

/**
 * 공유 버튼 컴포넌트
 * Web Share API를 사용하고, 지원하지 않는 경우 클립보드에 복사
 */
export function ShareButton({ title, reportId }: ShareButtonProps) {
  const [copied, setCopied] = useState(false);
  const [currentUrl, setCurrentUrl] = useState("");

  useEffect(() => {
    // 클라이언트에서만 URL 구성
    if (typeof window !== "undefined") {
      setCurrentUrl(window.location.href);
    }
  }, []);

  const handleShare = async () => {
    const url = currentUrl || `${window.location.origin}/report/${reportId}`;
    const shareData = {
      title: title,
      text: `${title} - 주식 동향 분석 보고서`,
      url: url,
    };

    try {
      // Web Share API 지원 확인 (모바일 브라우저 등)
      if (navigator.share && navigator.canShare && navigator.canShare(shareData)) {
        await navigator.share(shareData);
      } else {
        // 폴백: 클립보드에 링크 복사
        await navigator.clipboard.writeText(url);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }
    } catch (error) {
      // 사용자가 공유를 취소한 경우는 에러로 처리하지 않음
      if ((error as Error).name !== "AbortError") {
        // 클립보드 복사로 폴백
        try {
          await navigator.clipboard.writeText(url);
          setCopied(true);
          setTimeout(() => setCopied(false), 2000);
        } catch (clipboardError) {
          console.error("Failed to copy to clipboard:", clipboardError);
        }
      }
    }
  };

  return (
    <div className="relative">
      <button onClick={handleShare} className="p-2 hover:bg-muted rounded-lg transition-colors" aria-label="공유">
        {copied ? (
          <FiCheck className="w-5 h-5 text-green-600" />
        ) : (
          <FiShare2 className="w-5 h-5 text-muted-foreground" />
        )}
      </button>
      {copied && (
        <div className="absolute top-full right-0 mt-2 bg-gray-900 text-white text-xs px-3 py-2 rounded-lg shadow-lg z-50 whitespace-nowrap">
          링크가 복사되었습니다
        </div>
      )}
    </div>
  );
}
