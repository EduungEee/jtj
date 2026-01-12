import { NewsArticle } from "@/lib/api/reports";
import { FiExternalLink, FiCalendar, FiGlobe } from "react-icons/fi";

interface NewsListProps {
  articles: NewsArticle[];
}

/**
 * 뉴스 기사 리스트 컴포넌트
 * 특별한 디자인의 뉴스 카드
 */
export function NewsList({ articles }: NewsListProps) {
  if (articles.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-muted-foreground">뉴스 기사가 없습니다.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {articles.map((article, index) => (
        <article
          key={article.id}
          className="relative group overflow-hidden border rounded-lg hover:shadow-lg transition-all duration-300 bg-gradient-to-br from-card to-card/50 hover:from-card hover:to-card"
        >
          {/* 왼쪽 액센트 바 */}
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-primary via-primary/80 to-primary/60 group-hover:from-primary group-hover:via-primary group-hover:to-primary transition-all duration-300" />

          {/* 메인 컨텐츠 */}
          <div className="pl-5 pr-5 py-4">
            {/* 헤더: 날짜와 소스 */}
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2 flex-wrap">
                {article.published_at && (
                  <div className="flex items-center gap-1 px-2 py-0.5 bg-primary/10 rounded-full text-xs font-medium text-primary">
                    <FiCalendar className="w-2.5 h-2.5" />
                    <span>{new Date(article.published_at).toLocaleDateString("ko-KR")}</span>
                  </div>
                )}
                {article.source && (
                  <div className="flex items-center gap-1 px-2 py-0.5 bg-muted rounded-full text-xs text-muted-foreground">
                    <FiGlobe className="w-2.5 h-2.5" />
                    <span>{article.source}</span>
                  </div>
                )}
              </div>
            </div>

            {/* 제목 */}
            <h3 className="font-semibold text-lg mb-2 text-foreground group-hover:text-primary transition-colors pr-6">
              {article.title}
            </h3>

            {/* 내용 */}
            {article.content && (
              <p className="text-sm text-muted-foreground line-clamp-2 mb-3 leading-relaxed">{article.content}</p>
            )}

            {/* 링크 */}
            {article.url && (
              <a
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-primary/10 hover:bg-primary text-primary hover:text-white rounded-lg text-xs font-medium transition-all duration-300 hover:shadow-md"
              >
                <span>원문 보기</span>
                <FiExternalLink className="w-3.5 h-3.5 hover:translate-x-0.5 hover:-translate-y-0.5 transition-transform" />
              </a>
            )}
          </div>

          {/* 호버 시 배경 효과 */}
          <div className="absolute inset-0 bg-gradient-to-r from-primary/0 via-primary/0 to-primary/0 group-hover:from-primary/5 group-hover:via-primary/0 group-hover:to-primary/0 transition-all duration-300 pointer-events-none rounded-lg" />
        </article>
      ))}
    </div>
  );
}
