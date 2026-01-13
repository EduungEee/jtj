from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, DATE, DECIMAL, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
import sys
import os

# app 패키지 경로 추가
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.database import Base

# 보고서-뉴스 다대다 관계 테이블
report_news = Table(
    'report_news',
    Base.metadata,
    Column('report_id', Integer, ForeignKey('reports.id', ondelete='CASCADE'), primary_key=True),
    Column('news_id', Integer, ForeignKey('news_articles.id', ondelete='CASCADE'), primary_key=True)
)

class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    content = Column(Text)
    source = Column(String(255))
    url = Column(String(1000))
    published_at = Column(TIMESTAMP)
    collected_at = Column(TIMESTAMP, server_default=func.now())
    # embedding은 pgvector vector(1536) 타입이므로 SQLAlchemy 모델에서는 제외
    # SQL로 직접 저장/조회 (save_embedding_to_db 함수 사용)
    article_metadata = Column("metadata", JSONB)  # 벡터 DB metadata (title, url, published_date, collected_at 포함)

    # 관계
    reports = relationship("Report", secondary=report_news, back_populates="news_articles")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    summary = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())
    analysis_date = Column(DATE, nullable=False)

    # 관계
    news_articles = relationship("NewsArticle", secondary=report_news, back_populates="reports")
    industries = relationship("ReportIndustry", back_populates="report", cascade="all, delete-orphan")


class ReportIndustry(Base):
    __tablename__ = "report_industries"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey('reports.id', ondelete='CASCADE'), nullable=False)
    industry_name = Column(String(255), nullable=False)
    impact_level = Column(String(50))  # 'high', 'medium', 'low'
    impact_description = Column(Text)
    trend_direction = Column(String(50))  # 'positive', 'negative', 'neutral'
    created_at = Column(TIMESTAMP, server_default=func.now())

    # 관계
    report = relationship("Report", back_populates="industries")
    stocks = relationship("ReportStock", back_populates="industry", cascade="all, delete-orphan")


class ReportStock(Base):
    __tablename__ = "report_stocks"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey('reports.id', ondelete='CASCADE'), nullable=False)
    industry_id = Column(Integer, ForeignKey('report_industries.id', ondelete='CASCADE'), nullable=False)
    stock_code = Column(String(50))
    stock_name = Column(String(255))
    expected_trend = Column(String(50))  # 'up', 'down', 'neutral'
    confidence_score = Column(DECIMAL(3, 2))  # 0.00 ~ 1.00
    reasoning = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # 관계
    industry = relationship("ReportIndustry", back_populates="stocks")
