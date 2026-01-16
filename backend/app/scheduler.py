"""
스케줄러 모듈
APScheduler를 사용하여 주기적인 작업을 스케줄링합니다.
"""
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import pytz
import httpx
import sys
import os

# app 패키지 경로 추가
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# 전역 스케줄러 인스턴스
scheduler = AsyncIOScheduler(timezone=pytz.timezone('Asia/Seoul'))


async def collect_news_hourly():
    """
    1시간마다 실행되는 뉴스 수집 작업.
    POST /api/get_news API를 호출하여 최신 뉴스를 수집하고 저장합니다.
    """
    try:
        print("=" * 60)
        print(f"📰 뉴스 수집 스케줄러 실행: {datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # API 엔드포인트 호출
        api_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        get_news_url = f"{api_url}/api/get_news"
        
        # Query 파라미터 (comma-separated 형식)
        query = "주식,증시,코스피,코스닥,반도체,경제,금리,부동산,주가,투자"
        size = 10  # 무료 티어 제한: 최대 10개
        
        # Query 파라미터로 전달
        params = {
            "query": query,
            "size": size
        }
        
        print(f"📡 API 호출: POST {get_news_url}")
        print(f"   쿼리: {query}")
        print(f"   크기: {size}")
        
        async with httpx.AsyncClient(timeout=60.0) as client:  # 1분 타임아웃
            response = await client.post(get_news_url, params=params)
            
            if response.status_code == 200:
                result = response.json()
                collected_count = result.get("collected_count", 0)
                print(f"✅ 뉴스 수집 완료: {collected_count}개 저장됨")
                print("=" * 60)
                return result
            else:
                error_detail = response.text
                print(f"❌ API 호출 실패: {response.status_code}")
                print(f"응답: {error_detail}")
                print("=" * 60)
                raise Exception(f"API 호출 실패 ({response.status_code}): {error_detail}")
        
    except httpx.TimeoutException:
        print("❌ API 호출 타임아웃 (1분 초과)")
        print("=" * 60)
        raise
    except Exception as e:
        import traceback
        print(f"❌ 뉴스 수집 중 오류 발생: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        print("=" * 60)
        raise


async def run_daily_analysis():
    """
    매일 아침 6시에 실행되는 일일 분석 작업.
    POST /api/analyze API를 호출하여 벡터 DB에서 뉴스를 조회하고 분석합니다.
    """
    try:
        print("=" * 60)
        print(f"📊 일일 분석 스케줄러 실행: {datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # API 엔드포인트 호출
        api_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        analyze_url = f"{api_url}/api/analyze"
        
        # POST 요청 데이터
        request_data = {
            "force": False  # 이미 분석된 날짜는 재분석하지 않음
        }
        
        print(f"📡 API 호출: POST {analyze_url}")
        
        async with httpx.AsyncClient(timeout=300.0) as client:  # 5분 타임아웃
            response = await client.post(analyze_url, json=request_data)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 일일 분석 완료: 보고서 ID={result.get('report_id')}, 뉴스 {result.get('news_count')}개")
                print("=" * 60)
                return result
            elif response.status_code == 400 and "already_exists" in response.text:
                result = response.json()
                print(f"ℹ️  이미 분석된 보고서 존재: 보고서 ID={result.get('report_id')}")
                print("=" * 60)
                return result
            else:
                error_detail = response.text
                print(f"❌ API 호출 실패: {response.status_code}")
                print(f"응답: {error_detail}")
                print("=" * 60)
                raise Exception(f"API 호출 실패 ({response.status_code}): {error_detail}")
        
    except httpx.TimeoutException:
        print("❌ API 호출 타임아웃 (5분 초과)")
        print("=" * 60)
        raise
    except Exception as e:
        import traceback
        print(f"❌ 일일 분석 중 오류 발생: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        print("=" * 60)
        raise


def start_scheduler():
    """
    스케줄러를 시작하고 작업을 등록합니다.
    """
    if scheduler.running:
        print("⚠️  스케줄러가 이미 실행 중입니다.")
        return
    
    # 1시간마다 뉴스 수집 실행
    scheduler.add_job(
        collect_news_hourly,
        trigger=CronTrigger(minute=0, timezone='Asia/Seoul'),  # 매시간 정각
        id='hourly_news_collection',
        name='시간별 뉴스 수집',
        replace_existing=True
    )
    
    # 매일 아침 6시에 일일 분석 실행
    scheduler.add_job(
        run_daily_analysis,
        trigger=CronTrigger(hour=6, minute=0, timezone='Asia/Seoul'),
        id='daily_analysis',
        name='일일 뉴스 분석',
        replace_existing=True
    )
    
    scheduler.start()
    print("✅ 스케줄러가 시작되었습니다.")
    print("   - 매시간 정각(00분)에 뉴스 수집이 실행됩니다.")
    print("   - 매일 06:00에 일일 분석이 실행됩니다.")


def stop_scheduler():
    """
    스케줄러를 중지합니다.
    """
    if scheduler.running:
        scheduler.shutdown()
        print("✅ 스케줄러가 중지되었습니다.")
    else:
        print("⚠️  스케줄러가 실행 중이 아닙니다.")

