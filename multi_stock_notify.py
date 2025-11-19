import os
import json
import requests
from datetime import datetime, timedelta
import yfinance as yf
import time

TOKEN_FILE = "kakao_token.json"
MAX_RETRY = 3
MAX_MESSAGE_LEN = 900  # 카톡 메시지 안전 길이

REST_KEY = os.getenv("KAKAO_REST_API_KEY")
REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI")
ACCESS_TOKEN = os.getenv("KAKAO_ACCESS_TOKEN")
REFRESH_TOKEN = os.getenv("KAKAO_REFRESH_TOKEN")  # 최초는 "EMPTY" 같은 문자열

class KakaoNotifier:
    def __init__(self):
            global REFRESH_TOKEN, ACCESS_TOKEN

        # 1) 최초 실행 → refresh_token 이 EMPTY 같은 값일 때
        if REFRESH_TOKEN.strip().upper() in ["EMPTY", "", "NONE", "NULL"]:
            print("⚠️ 최초 상태: Refresh Token 없음 → 최초 발급 시도")

            new_refresh = request_new_refresh_token()
            if not new_refresh:
                print("❌ 최초 refresh_token 발급 실패 → 종료")
                return

            # GitHub Secrets 에 refresh_token 저장 요청
            update_github_secret("NEW_REFRESH_TOKEN", new_refresh)
            print("🟢 최초 refresh_token 저장 준비 완료")
            return

        # 2) 기존 refresh_token 으로 access 토큰 재발급
        new_access, new_refresh = refresh_access_token(REFRESH_TOKEN)

        if not new_access:
            print("❌ access_token 갱신 실패 → 종료")
            return

        # ACCESS_TOKEN Secrets updated
        update_github_secret("NEW_ACCESS_TOKEN", new_access)

        # refresh_token 도 새로 오면 갱신
        if new_refresh:
            update_github_secret("NEW_REFRESH_TOKEN", new_refresh)

        print("🟢 Kakao Token Update Completed")

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



    def send_message(self, text):
        # 메시지 길이 분할
        messages = [text[i:i+MAX_MESSAGE_LEN] for i in range(0, len(text), MAX_MESSAGE_LEN)]

        for msg in messages:
            for attempt in range(1, MAX_RETRY+1):
                try:
                    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
                    headers = {
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    }
                    template = {
                        "object_type": "text",
                        "text": msg,
                        "link": {"web_url": "https://finance.yahoo.com"}
                    }
                    data = {"template_object": json.dumps(template, ensure_ascii=False)}
                    res = requests.post(url, headers=headers, data=data, timeout=10)
                    print(f"시도 {attempt} 상태:", res.status_code, res.text)

                    if res.status_code == 401:
                        print("401 Unauthorized → access_token 갱신 시도")
                        if not self.refresh_access_token():
                            print("❌ access_token 갱신 실패, 수동 갱신 필요")
                            break
                        continue

                    res.raise_for_status()
                    print("✅ 카톡 메시지 전송 성공")
                    break

                except Exception as e:
                    print(f"전송 실패 시도 {attempt}: {e}")
                    if attempt < MAX_RETRY:
                        time.sleep(2)
                    else:
                        print("❌ 최종 실패")

    # --- 주식 정보 조회 ---
    def get_stock_info(tickers=["AAPL","TSLA","MSFT"]):
        messages = []
        for t in tickers:
            stock = yf.Ticker(t)
            data = stock.history(period="1d")
            if data.empty:
                messages.append(f"{t}: 데이터 없음")
                continue
            last = data.iloc[-1]
            diff = last['Close'] - last['Open']
            arrow = "🔺" if diff > 0 else ("🔻" if diff < 0 else "➡️")
            messages.append(f"{t}: {last['Close']:.2f} {arrow} ({diff:+.2f})")
        return "\n".join(messages)

# --- 실행 ---
if __name__ == "__main__":
    try:
        notifier = KakaoNotifier()
        stock_message = get_stock_info(["AAPL","TSLA","MSFT","GOOG","AMZN"])
        today = datetime.now().strftime("%Y-%m-%d")
        message = f"📊 {today} 주식 정보\n{stock_message}"
        notifier.send_message(message)
    except Exception as e:
        print("스크립트 실행 중 오류:", e)