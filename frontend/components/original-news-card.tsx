import { NewsArticle } from "@/lib/api/reports";
import { FiFileText, FiExternalLink } from "react-icons/fi";

interface OriginalNewsCardProps {
  article: NewsArticle;
}

/**
 * 원본 뉴스 카드 컴포넌트
 */
export function OriginalNewsCard({ article }: OriginalNewsCardProps) {
  const formatDateTime = (dateString: string | null) => {
    if (!dateString) return "";
    const date = new Date(dateString);
    return date.toLocaleString("ko-KR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="p-6 bg-white rounded-lg border shadow-sm mb-6">
      <div className="flex items-center gap-2 mb-4">
        <FiFileText className="w-5 h-5 text-primary" />
        <h2 className="text-xl font-semibold text-foreground">원본 뉴스</h2>
      </div>
      <div className="mb-3">
        {article.source && <span className="text-sm font-medium text-foreground">{article.source}</span>}
        {article.published_at && (
          <span className="text-sm text-muted-foreground ml-2">{formatDateTime(article.published_at)}</span>
        )}
      </div>
      <h3 className="text-lg font-semibold text-foreground mb-3">{article.title}</h3>
      {article.content && (
        <p className="text-sm text-muted-foreground leading-relaxed mb-4 line-clamp-3">{article.content}</p>
      )}
      {article.url && (
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 text-primary hover:underline text-sm font-medium"
        >
          원문 보기
          <FiExternalLink className="w-4 h-4" />
        </a>
      )}
    </div>
  );
}
