"use client";

import { useState, useRef, useEffect } from "react";
import { FiMenu, FiX } from "react-icons/fi";
import { HiArrowTrendingUp } from "react-icons/hi2";
import { gsap } from "gsap";
import { cn } from "@/lib/utils";

/**
 * 반투명 Navbar 컴포넌트
 * Desktop과 Mobile 모두 지원
 * Magic UI 효과 포함
 */
export function Navbar() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const menuContentRef = useRef<HTMLDivElement>(null);
  const menuItemsRef = useRef<HTMLAnchorElement[]>([]);

  const navItems = [
    { label: "오늘의 보고서", href: "#today-reports" },
    { label: "서비스 소개", href: "#service-intro" },
    { label: "어떻게 작동하나요?", href: "#features" },
  ];

  useEffect(() => {
    if (!menuRef.current || !menuContentRef.current) return;

    if (isMobileMenuOpen) {
      // 메뉴 열기 애니메이션
      const tl = gsap.timeline();

      // 컨테이너 애니메이션
      tl.fromTo(
        menuRef.current,
        {
          height: 0,
          opacity: 0,
        },
        {
          height: "auto",
          opacity: 1,
          duration: 0.4,
          ease: "power3.out",
        },
      );

      // 메뉴 컨텐츠 애니메이션
      tl.fromTo(
        menuContentRef.current,
        {
          y: -20,
          opacity: 0,
          scale: 0.95,
        },
        {
          y: 0,
          opacity: 1,
          scale: 1,
          duration: 0.3,
          ease: "back.out(1.2)",
        },
        "-=0.2",
      );

      // 각 메뉴 아이템 순차 애니메이션
      menuItemsRef.current.forEach((item, index) => {
        if (item) {
          tl.fromTo(
            item,
            {
              x: -20,
              opacity: 0,
            },
            {
              x: 0,
              opacity: 1,
              duration: 0.25,
              ease: "power2.out",
            },
            index * 0.05,
          );
        }
      });
    } else {
      // 메뉴 닫기 애니메이션
      const tl = gsap.timeline();

      // 메뉴 아이템 역순 애니메이션
      menuItemsRef.current.forEach((item, index) => {
        if (item) {
          tl.to(
            item,
            {
              x: -20,
              opacity: 0,
              duration: 0.15,
              ease: "power2.in",
            },
            index * 0.03,
          );
        }
      });

      // 메뉴 컨텐츠 애니메이션
      tl.to(
        menuContentRef.current,
        {
          y: -10,
          opacity: 0,
          scale: 0.95,
          duration: 0.2,
          ease: "power2.in",
        },
        "-=0.1",
      );

      // 컨테이너 애니메이션
      tl.to(
        menuRef.current,
        {
          height: 0,
          opacity: 0,
          duration: 0.3,
          ease: "power2.in",
        },
        "-=0.1",
      );
    }
  }, [isMobileMenuOpen]);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 w-full">
      <div className="max-w-5xl mx-auto">
        {/* 반투명 배경 with gradient border effect */}
        <div className="absolute inset-0 bg-white/80 backdrop-blur-md border-b border-white/20" />

        {/* Magic UI: Border beam effect */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-primary/50 to-transparent animate-pulse" />
        </div>

        {/* Navbar 컨텐츠 */}
        <div className="relative container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            {/* 로고 */}
            <a href="/" className="flex items-center gap-3 z-10 group">
              <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center shrink-0">
                <HiArrowTrendingUp className="w-6 h-6 text-primary-foreground" />
              </div>
              <span className="text-xl font-bold text-foreground">MarketReport</span>
            </a>

            {/* Desktop Navigation */}
            <div className="hidden md:flex items-center gap-8">
              {navItems.map((item) => (
                <a
                  key={item.label}
                  href={item.href}
                  className={cn(
                    "relative text-sm font-medium text-foreground/80",
                    "transition-all duration-300 hover:text-primary",
                    "after:absolute after:bottom-0 after:left-0 after:w-0 after:h-0.5",
                    "after:bg-gradient-to-r after:from-primary after:to-primary/60",
                    "after:transition-all after:duration-300 after:rounded-full",
                    "hover:after:w-full",
                    "before:absolute before:inset-0 before:rounded-lg",
                    "before:bg-primary/5 before:opacity-0 before:transition-opacity",
                    "hover:before:opacity-100 hover:px-3 hover:py-1.5",
                  )}
                >
                  {item.label}
                </a>
              ))}
            </div>

            {/* Mobile Menu Button */}
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="md:hidden z-10 p-2 rounded-lg hover:bg-white/20 transition-all active:scale-95"
              aria-label={isMobileMenuOpen ? "메뉴 닫기" : "메뉴 열기"}
            >
              {isMobileMenuOpen ? (
                <FiX className="w-6 h-6 text-foreground transition-all duration-300" />
              ) : (
                <FiMenu className="w-6 h-6 text-foreground transition-all duration-300" />
              )}
            </button>
          </div>

          {/* Mobile Menu with GSAP animation */}
          <div ref={menuRef} className="md:hidden overflow-hidden" style={{ height: 0, opacity: 0 }}>
            <div
              ref={menuContentRef}
              className="flex mt-4 pb-4  flex-col gap-2 bg-white/60 backdrop-blur-md rounded-lg p-4 border border-white/20 shadow-lg"
            >
              {navItems.map((item, index) => (
                <a
                  key={item.label}
                  ref={(el) => {
                    if (el) menuItemsRef.current[index] = el;
                  }}
                  href={item.href}
                  onClick={() => setIsMobileMenuOpen(false)}
                  className={cn(
                    "text-sm font-medium text-foreground/80",
                    "transition-all duration-300 hover:text-primary",
                    "py-3 px-4 rounded-lg hover:bg-white/40",
                    "hover:translate-x-1 hover:shadow-sm",
                    "border border-transparent hover:border-primary/20",
                  )}
                >
                  {item.label}
                </a>
              ))}
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}
