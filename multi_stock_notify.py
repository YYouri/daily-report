import os
import json
import requests
from datetime import datetime, timedelta
import yfinance as yf
import time

TOKEN_FILE = "kakao_token.json"
MAX_RETRY = 3
MAX_MESSAGE_LEN = 900

REST_KEY = os.getenv("KAKAO_REST_API_KEY")
REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI")
ACCESS_TOKEN = os.getenv("KAKAO_ACCESS_TOKEN")
REFRESH_TOKEN = os.getenv("KAKAO_REFRESH_TOKEN")  # 최초는 "EMPTY"

###############################################
# 필요한 함수 정의
###############################################
def update_github_secret(name, value):
    print(f"👉 (DEBUG) GitHub Secret 갱신 요청: {name} = {value[:10]}...")

def request_new_refresh_token():
    """
    최초 실행 시 access_token → refresh_token 발급
    """
    print("🔄 최초 refresh_token 발급 요청...")

    URL = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": REST_KEY,
        "redirect_uri": REDIRECT_URI,
        "code": ACCESS_TOKEN,  # AUTH_CODE 없이 최초 발급 불가 → ACCESS_TOKEN 사용 X
    }

    print("❗ 현재 구조로는 refresh_token 최초 발급 불가능 (auth_code 필요)")
    return None  # 추후 수정 필요

def refresh_access_token(refresh_token):
    """
    refresh_token 으로 access_token 갱신
    """
    print("🔄 refresh_token 으로 access_token 갱신 요청...")

    URL = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": REST_KEY,
        "refresh_token": refresh_token,
    }

    res = requests.post(URL, data=data)
    print(f"🔍 kakao응답 = {res.status_code}, {res.text}")

    if res.status_code != 200:
        return None, None

    json_data = res.json()
    new_access = json_data.get("access_token")
    new_refresh = json_data.get("refresh_token")  # 새로 내려올 수도 있음

    return new_access, new_refresh


###############################################
# Kakao Notifier Class
###############################################
class KakaoNotifier:
    def __init__(self):
        global REFRESH_TOKEN, ACCESS_TOKEN

        print("🔍 환경 변수 RAW 출력 시작 (⚠️ 디버깅용, 배포 전 반드시 삭제!)")
        print(f" - REST_KEY       = {REST_KEY}")
        print(f" - ACCESS_TOKEN   = {ACCESS_TOKEN}")
        print(f" - REFRESH_TOKEN  = {REFRESH_TOKEN}")
        print(f" - REDIRECT_URI   = {REDIRECT_URI}")

        print("🔍 상태 체크 시작")
        if REFRESH_TOKEN is None:
            print(" - REFRESH_TOKEN: None")
        elif REFRESH_TOKEN.strip() == "":
            print(" - REFRESH_TOKEN: '' (빈 문자열)")
        else:
            print(" - REFRESH_TOKEN 정상 값")

        # 1) 최초 실행: refresh_token 없음
        if not REFRESH_TOKEN or REFRESH_TOKEN.strip().upper() in ["NONE", "EMPTY", "", "NULL"]:
            print("⚠️ 최초 상태: Refresh Token 없음 → 최초 발급 시도")

            new_refresh = request_new_refresh_token()
            if not new_refresh:
                print("❌ 최초 refresh_token 발급 실패 → 종료")
                return

            update_github_secret("NEW_REFRESH_TOKEN", new_refresh)
            print("🟢 최초 refresh_token 저장 준비 완료")
            REFRESH_TOKEN = new_refresh
            return

        # 2) 기존 refresh_token 활용해 access_token 재발급
        new_access, new_refresh = refresh_access_token(REFRESH_TOKEN)

        if not new_access:
            print("❌ access_token 갱신 실패 → 종료")
            return

        update_github_secret("NEW_ACCESS_TOKEN", new_access)

        if new_refresh:
            update_github_secret("NEW_REFRESH_TOKEN", new_refresh)

        ACCESS_TOKEN = new_access
        print("🟢 Kakao Token Update Completed")


###############################################
# 실행
###############################################
if __name__ == "__main__":
    notifier = KakaoNotifier()