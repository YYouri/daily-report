import os
import requests
import json

REST_KEY = os.getenv("KAKAO_REST_API_KEY")
REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI")
ACCESS_TOKEN = os.getenv("KAKAO_ACCESS_TOKEN")
REFRESH_TOKEN = os.getenv("KAKAO_REFRESH_TOKEN")  # 최초는 "EMPTY" 같은 문자열

def update_github_secret(name, value):
    """
    GitHub Actions 에서 secret 업데이트 요청을 Workflow Dispatch 로 전달
    (Actions 내부에서는 직접 secret 갱신이 불가)
    → Actions environment variable 로 출력하여,
      다음 step 이 github API 로 secret 갱신 처리
    """
    print(f"::set-output name={name}::{value}")


def request_new_refresh_token():
    """
    최초 상태에서 refresh token 이 없는 경우
    access_token 검증을 통해 refresh_token 발급
    """
    url = "https://kapi.kakao.com/v1/user/access_token_info"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        print("❌ access_token invalid → refresh_token 최초 발급 불가")
        return None

    print("🔄 access_token 유효 → refresh_token 최초 발급 시작")

    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": REST_KEY,
        "refresh_token": ACCESS_TOKEN  # ❗ 최초에는 access_token을 대체 사용
    }
    r = requests.post(url, data=data)

    if r.status_code != 200:
        print("❌ 최초 refresh_token 발급 실패:", r.text)
        return None

    new_refresh_token = r.json().get("refresh_token")
    print("✅ 최초 refresh_token 발급 성공")

    return new_refresh_token


def refresh_access_token(refresh_token):
    """
    정상적인 refresh_token 으로 access_token 재발급
    """
    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": REST_KEY,
        "refresh_token": refresh_token
    }

    r = requests.post(url, data=data)

    if r.status_code != 200:
        print("❌ refresh_token 갱신 실패:", r.text)
        return None, None

    new_access = r.json().get("access_token")
    new_refresh = r.json().get("refresh_token")  # 보통 없음, 있을 때만 갱신

    print("🔄 access_token 갱신 완료")
    return new_access, new_refresh


def main():
    global REFRESH_TOKEN, ACCESS_TOKEN
    print("🔍 환경 변수 RAW 출력 시작 (⚠️ 디버깅용, 배포 전 반드시 삭제!)")

    print(f" - REST_KEY            = {REST_KEY}")
    print(f" - ACCESS_TOKEN        = {ACCESS_TOKEN}")
    print(f" - REFRESH_TOKEN       = {REFRESH_TOKEN}")
    print(f" - REDIRECT_URI        = {REDIRECT_URI}")

    print("🔍 상태 체크 시작")



if __name__ == "__main__":
    main()