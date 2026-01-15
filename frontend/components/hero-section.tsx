"use client";

import { FiStar, FiArrowRight, FiTrendingUp, FiBarChart2 } from "react-icons/fi";
import { SignUpButton, SignedIn, SignedOut } from "@clerk/nextjs";
import Link from "next/link";

/**
 * Hero 섹션 컴포넌트
 * 홈페이지 상단의 주요 가입 유도 섹션
 */
export function HeroSection() {
  return (
    <section id="service-intro" className="container mx-auto px-4 py-16 scroll-mt-20">
      <div className="max-w-4xl mx-auto text-center">
        {/* 서비스 태그 */}
        <div className="inline-flex items-center gap-2 px-4 py-1.5 mb-8 bg-pink-50 border border-red-200 rounded-full">
          <FiStar className="w-4 h-4 text-red-500" />
          <span className="text-sm font-medium text-red-600">AI 기반 주식 분석 서비스</span>
        </div>

        {/* 메인 제목 */}
        <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold mb-6 leading-tight">
          <span className="text-foreground">뉴스로 예측하는</span>
          <br />
          <span className="text-primary">내일의 주식 시장</span>
        </h1>

        {/* 설명 텍스트 */}
        <p className="text-lg md:text-xl text-muted-foreground mb-10 max-w-2xl mx-auto leading-relaxed">
          AI가 최신 뉴스를 분석하여 사회적 파급효과를 예측하고, 영향받는 산업과 유망 주식을 알려드립니다. 매일 아침,
          맞춤형 분석 보고서를 받아보세요.
        </p>

        {/* CTA 버튼 */}
        <div className="mb-4">
          <SignedOut>
            <SignUpButton mode="modal">
              <button className="inline-flex items-center gap-2 px-8 py-4 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition-all duration-300 text-lg font-semibold shadow-lg hover:shadow-xl hover:scale-105 active:scale-95">
                <span>로그인 하기</span>
                <FiArrowRight className="w-5 h-5" />
              </button>
            </SignUpButton>
          </SignedOut>
          <SignedIn>
            <Link
              href="#recent-reports"
              className="inline-flex items-center gap-2 px-8 py-4 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition-all duration-300 text-lg font-semibold shadow-lg hover:shadow-xl hover:scale-105 active:scale-95"
            >
              <span>보고서 보기</span>
              <FiArrowRight className="w-5 h-5" />
            </Link>
          </SignedIn>
        </div>

        {/* 서브 텍스트 */}
        <p className="text-sm text-muted-foreground mb-16">무료로 시작하기 · 신용카드 필요 없음</p>

        {/* 통계 섹션 */}
        <div className="grid grid-cols-3 gap-2 md:gap-8 pt-8 border-t border-border">
          {/* 분석된 뉴스 */}
          <div className="flex flex-col items-center">
            <FiTrendingUp className="w-5 h-5 md:w-8 md:h-8 text-primary mb-2 md:mb-3" />
            <div className="text-xl md:text-4xl font-bold text-foreground mb-0.5 md:mb-1">1,200+</div>
            <div className="text-xs md:text-sm text-muted-foreground">분석된 뉴스</div>
          </div>

          {/* 예측 정확도 */}
          <div className="flex flex-col items-center">
            <FiBarChart2 className="w-5 h-5 md:w-8 md:h-8 text-primary mb-2 md:mb-3" />
            <div className="text-xl md:text-4xl font-bold text-foreground mb-0.5 md:mb-1">85%</div>
            <div className="text-xs md:text-sm text-muted-foreground">예측 정확도</div>
          </div>

          {/* 구독자 수 */}
          <div className="flex flex-col items-center">
            <FiStar className="w-5 h-5 md:w-8 md:h-8 text-primary mb-2 md:mb-3" />
            <div className="text-xl md:text-4xl font-bold text-foreground mb-0.5 md:mb-1">5,000+</div>
            <div className="text-xs md:text-sm text-muted-foreground">구독자 수</div>
          </div>
        </div>
      </div>
    </section>
  );
}
