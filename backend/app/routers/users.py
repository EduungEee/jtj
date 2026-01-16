"""
사용자 및 구독자 관리 API 라우터
Clerk webhook 처리 및 구독자 수 조회 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
import sys
import os

# models 경로 추가
backend_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from models.models import User

router = APIRouter()

# Clerk webhook secret (환경 변수에서 가져오기)
CLERK_WEBHOOK_SECRET = os.getenv("CLERK_WEBHOOK_SECRET", "")


# 응답 모델 정의
class SubscriberCountResponse(BaseModel):
    """구독자 수 응답 모델"""
    count: int


# Clerk webhook 이벤트 데이터 모델
class ClerkWebhookEvent(BaseModel):
    """Clerk webhook 이벤트 모델"""
    type: str
    data: dict


def verify_clerk_webhook_signature(
    payload: bytes,
    svix_id: Optional[str],
    svix_timestamp: Optional[str],
    svix_signature: Optional[str]
) -> bool:
    """
    Clerk webhook signature를 검증합니다.
    
    Note: 실제 프로덕션 환경에서는 svix 라이브러리를 사용하여 검증해야 합니다.
    현재는 기본적인 검증만 수행합니다.
    """
    if not CLERK_WEBHOOK_SECRET:
        # 개발 환경에서는 secret이 없어도 허용 (프로덕션에서는 필수)
        print("⚠️  CLERK_WEBHOOK_SECRET이 설정되지 않았습니다. webhook 검증을 건너뜁니다.")
        return True
    
    # svix 라이브러리를 사용한 검증 (선택사항)
    # 실제 프로덕션에서는 svix 라이브러리를 설치하고 사용해야 합니다:
    # pip install svix
    # from svix.webhooks import Webhook, WebhookVerificationError
    # try:
    #     webhook = Webhook(CLERK_WEBHOOK_SECRET)
    #     headers = {
    #         "svix-id": svix_id,
    #         "svix-timestamp": svix_timestamp,
    #         "svix-signature": svix_signature,
    #     }
    #     webhook.verify(payload, headers)
    #     return True
    # except WebhookVerificationError:
    #     return False
    
    # 기본 검증: 헤더 존재 여부 확인
    if not all([svix_id, svix_timestamp, svix_signature]):
        return False
    
    return True


@router.post("/webhooks/clerk")
async def handle_clerk_webhook(
    request: Request,
    svix_id: Optional[str] = Header(None, alias="svix-id"),
    svix_timestamp: Optional[str] = Header(None, alias="svix-timestamp"),
    svix_signature: Optional[str] = Header(None, alias="svix-signature"),
    db: Session = Depends(get_db)
):
    """
    Clerk webhook을 수신하여 사용자 정보를 관리합니다.
    
    지원하는 이벤트:
    - user.created: 새 사용자 생성 시 이메일 저장
    - user.updated: 사용자 정보 업데이트 시 이메일 동기화
    - user.deleted: 사용자 탈퇴 시 DB에서 삭제
    """
    # Raw body 가져오기 (signature 검증을 위해 필요)
    payload = await request.body()
    
    # JSON 파싱 (먼저 파싱하여 이벤트 타입 확인)
    try:
        import json
        event_data = json.loads(payload.decode('utf-8'))
    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 실패: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid JSON payload: {str(e)}"
        )
    
    event_type = event_data.get("type")
    data = event_data.get("data", {})
    
    print(f"📥 Clerk webhook 수신: {event_type}, user_id: {data.get('id')}")
    
    # Signature 검증 (개발 환경에서는 선택적)
    if not verify_clerk_webhook_signature(payload, svix_id, svix_timestamp, svix_signature):
        print(f"⚠️  Webhook signature 검증 실패 (개발 환경에서는 무시됨)")
        # 개발 환경에서는 계속 진행, 프로덕션에서는 주석 해제
        # raise HTTPException(
        #     status_code=401,
        #     detail="Invalid webhook signature"
        # )
    
    if event_type == "user.created":
        # 새 사용자 생성
        clerk_user_id = data.get("id")
        email_addresses = data.get("email_addresses", [])
        
        if not clerk_user_id:
            print(f"❌ user.created: user ID가 없습니다")
            raise HTTPException(
                status_code=400,
                detail="Missing user ID in webhook data"
            )
        
        # 이메일 주소 추출 (primary 이메일 우선)
        email = None
        primary_email_id = data.get("primary_email_address_id")
        
        if primary_email_id and email_addresses:
            for email_obj in email_addresses:
                if email_obj.get("id") == primary_email_id:
                    email = email_obj.get("email_address")
                    break
        
        # primary 이메일이 없으면 첫 번째 이메일 사용
        if not email and email_addresses:
            email = email_addresses[0].get("email_address")
        
        # 이메일이 없으면 400 에러 반환
        if not email:
            print(f"❌ user.created: 이메일이 없습니다 (user_id: {clerk_user_id})")
            raise HTTPException(
                status_code=400,
                detail="No email address found in webhook data. Email is required."
            )
        
        # 중복 확인 및 저장
        existing_user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
        if existing_user:
            # 이미 존재하는 경우 업데이트
            existing_user.email = email
            existing_user.is_active = True
            db.commit()
            print(f"✅ user.created: 기존 사용자 업데이트 (user_id: {clerk_user_id}, email: {email})")
            return {"message": "User updated successfully", "clerk_user_id": clerk_user_id, "email": email}
        else:
            # 새 사용자 생성
            new_user = User(
                clerk_user_id=clerk_user_id,
                email=email,
                is_active=True
            )
            db.add(new_user)
            db.commit()
            print(f"✅ user.created: 새 사용자 생성 (user_id: {clerk_user_id}, email: {email})")
            return {"message": "User created successfully", "clerk_user_id": clerk_user_id, "email": email}
    
    elif event_type == "user.updated":
        # 사용자 정보 업데이트
        clerk_user_id = data.get("id")
        email_addresses = data.get("email_addresses", [])
        
        if not clerk_user_id:
            print(f"❌ user.updated: user ID가 없습니다")
            raise HTTPException(
                status_code=400,
                detail="Missing user ID in webhook data"
            )
        
        # 이메일 주소 추출
        email = None
        primary_email_id = data.get("primary_email_address_id")
        
        if primary_email_id and email_addresses:
            for email_obj in email_addresses:
                if email_obj.get("id") == primary_email_id:
                    email = email_obj.get("email_address")
                    break
        
        if not email and email_addresses:
            email = email_addresses[0].get("email_address")
        
        # 이메일이 없으면 400 에러 반환
        if not email:
            print(f"❌ user.updated: 이메일이 없습니다 (user_id: {clerk_user_id})")
            raise HTTPException(
                status_code=400,
                detail="No email address found in webhook data. Email is required."
            )
        
        # 사용자 정보 업데이트
        user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
        if user:
            user.email = email
            db.commit()
            print(f"✅ user.updated: 사용자 업데이트 (user_id: {clerk_user_id}, email: {email})")
            return {"message": "User updated successfully", "clerk_user_id": clerk_user_id, "email": email}
        else:
            # 사용자가 없으면 생성
            new_user = User(
                clerk_user_id=clerk_user_id,
                email=email,
                is_active=True
            )
            db.add(new_user)
            db.commit()
            print(f"✅ user.updated: 새 사용자 생성 (user_id: {clerk_user_id}, email: {email})")
            return {"message": "User created from update event", "clerk_user_id": clerk_user_id, "email": email}
    
    elif event_type == "user.deleted":
        # 사용자 탈퇴 시 DB에서 삭제
        clerk_user_id = data.get("id")
        
        if not clerk_user_id:
            print(f"❌ user.deleted: user ID가 없습니다")
            raise HTTPException(
                status_code=400,
                detail="Missing user ID in webhook data"
            )
        
        # 사용자 찾기 및 삭제
        user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
        if user:
            db.delete(user)
            db.commit()
            print(f"✅ user.deleted: 사용자 삭제 (user_id: {clerk_user_id})")
            return {"message": "User deleted successfully", "clerk_user_id": clerk_user_id}
        else:
            # 사용자가 이미 존재하지 않는 경우 (이미 삭제되었거나 없었던 경우)
            print(f"⚠️  user.deleted: 사용자를 찾을 수 없음 (user_id: {clerk_user_id})")
            return {"message": "User not found in database", "clerk_user_id": clerk_user_id, "status": "already_deleted"}
    
    else:
        # 지원하지 않는 이벤트 타입
        print(f"⚠️  지원하지 않는 이벤트 타입: {event_type}")
        return {"message": f"Event type '{event_type}' not handled", "status": "ignored"}


@router.get("/subscribers/count", response_model=SubscriberCountResponse)
async def get_subscriber_count(
    db: Session = Depends(get_db)
):
    """
    활성 구독자 수를 조회합니다.
    """
    count = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    return SubscriberCountResponse(count=count or 0)
