"use client";

import { FiArrowRight } from "react-icons/fi";
import { SignUpButton, SignedIn, SignedOut } from "@clerk/nextjs";
import Link from "next/link";

/**
 * CTA (Call to Action) 섹션 컴포넌트
 * 로그인 상태에 따라 다른 버튼을 표시합니다.
 */
export function CTASection() {
  return (
    <section className="container mx-auto px-4 py-16">
      <div className="max-w-4xl mx-auto">
        <div className="bg-primary rounded-2xl p-8 md:p-12 text-center">
          {/* 제목 */}
          <h2 className="text-3xl md:text-4xl font-bold mb-4 text-primary-foreground">지금 바로 시작하세요</h2>

          {/* 설명 */}
          <p className="text-lg md:text-xl text-gray-100 mb-8 max-w-xl mx-auto">
            매일 아침, AI가 분석한 주식 시장 인사이트를 이메일로 받아보세요.
          </p>

          {/* 버튼 - 로그인 상태에 따라 다르게 표시 */}
          <div className="mb-4">
            <SignedOut>
              <SignUpButton mode="modal">
                <button className="inline-flex items-center gap-2 px-8 py-4 bg-white text-primary rounded-lg hover:opacity-90 transition-all duration-300 text-lg font-semibold shadow-lg hover:shadow-xl hover:scale-105 active:scale-95">
                  <span>시작하기</span>
                  <FiArrowRight className="w-5 h-5" />
                </button>
              </SignUpButton>
            </SignedOut>
            <SignedIn>
              <Link
                href="/#recent-reports"
                className="inline-flex items-center gap-2 px-8 py-4 bg-white text-primary rounded-lg hover:opacity-90 transition-all duration-300 text-lg font-semibold shadow-lg hover:shadow-xl hover:scale-105 active:scale-95"
              >
                <span>보고서 보기</span>
                <FiArrowRight className="w-5 h-5" />
              </Link>
            </SignedIn>
          </div>

          {/* 서브 텍스트 */}
          <p className="text-sm text-gray-100">구독은 무료이며, 언제든지 취소할 수 있습니다.</p>
        </div>
      </div>
    </section>
  );
}
