"use client";

import { FiArrowRight, FiSun, FiSunrise } from "react-icons/fi";
import { SignUpButton, SignedOut } from "@clerk/nextjs";

/**
 * 보고서 페이지용 CTA 섹션
 * 로그인하지 않은 사용자에게만 표시됩니다.
 * 메인 콘텐츠 위에 오버레이로 표시됩니다.
 */
export function ReportCTASection() {
  return (
    <SignedOut>
      <div className="w-full py-10 px-4">
        <div className="max-w-2xl mx-auto flex flex-col text-center">
          <FiSun className="size-10 mb-4 sm:size-14 text-primary mx-auto" />
          <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold mb-4 text-foreground leading-tight">
            <span className="inline-flex items-center gap-2">매일 아침</span>
            <br /> 분석 보고서를 받아보세요
          </h2>
          <p className="text-base sm:text-lg text-muted-foreground mb-8">
            AI가 분석한 최신 주식 동향을 이메일로 전달해 드립니다
          </p>
          <SignUpButton mode="modal">
            <div className="w-full">
              <button className="inline-flex cursor-pointer items-center gap-2 px-6 py-3 sm:px-8 sm:py-4 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition-all duration-300 text-base sm:text-lg font-semibold shadow-lg hover:shadow-xl">
                <span>무료로 시작하기</span>
                <FiArrowRight className="w-4 h-4 sm:w-5 sm:h-5" />
              </button>
            </div>
          </SignUpButton>
        </div>
      </div>
    </SignedOut>
  );
}
