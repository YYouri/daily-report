import os
import json
import requests
from datetime import datetime, timedelta
import yfinance as yf
import time

TOKEN_FILE = "kakao_token.json"
MAX_RETRY = 3
MAX_MESSAGE_LEN = 900  # 카톡 메시지 안전 길이

class KakaoNotifier:
    def __init__(self):
        self.rest_key = os.getenv("KAKAO_REST_API_KEY")
        self.redirect_uri = os.getenv("KAKAO_REDIRECT_URI")

        # 초기값: Secrets에서 가져옴
        self.access_token = os.getenv("KAKAO_ACCESS_TOKEN", "")
        self.refresh_token = os.getenv("KAKAO_REFRESH_TOKEN", "")

        # 로컬에 저장된 token 파일 우선 적용
        self.load_local_token()

        # 토큰 유효성 확인 및 필요 시 자동 갱신
        self.validate_and_refresh_tokens()

     # -------------------------------
    # 1. LOCAL TOKEN LOAD
    # -------------------------------
    def load_local_token(self):
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.access_token = data.get("access_token", self.access_token)
                    self.refresh_token = data.get("refresh_token", self.refresh_token)
                print("📌 로컬 토큰 로드 완료")
            except:
                print("⚠ 로컬 토큰 로드 실패 → 기본값 사용")

        else:
            # JSON 파일 없으면 만들어줌
            self.save_local_token()
            print("📌 로컬 토큰 파일 생성")

    # -------------------------------
    # 2. LOCAL TOKEN SAVE
    # -------------------------------
    def save_local_token(self):
        data = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token
        }
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # -------------------------------
    # 3. REFRESH TOKEN 발급
    # 최초 실행 + refresh_token 오류 시 사용
    # -------------------------------
    def issue_refresh_token_via_access(self):
        print("🔄 access_token 으로 refresh_token 발급 시도...")

        url = "https://kapi.kakao.com/v2/user/me"

        headers = {"Authorization": f"Bearer {self.access_token}"}

        # user/me 호출 → 정상일 경우 refresh_token 포함됨
        res = requests.post(url, headers=headers)

        if res.status_code == 401:
            print("❌ access_token 자체가 유효하지 않음 → 새로 발급 필요")
            return False

        if "refresh_token" not in res.headers:
            print("⚠ 응답에 refresh_token 없음 → 재시도 필요")
            return False

        # refresh_token 추출
        self.refresh_token = res.headers["refresh_token"]
        print("✅ refresh_token 발급 성공:", self.refresh_token)

        self.save_local_token()
        return True

    # -------------------------------
    # 4. REFRESH TOKEN으로 ACCESS 갱신
    # -------------------------------
    def refresh_access_token(self):
        print("🔄 refresh_token으로 access_token 갱신 시도...")

        url = "https://kauth.kakao.com/oauth/token"

        data = {
            "grant_type": "refresh_token",
            "client_id": self.rest_key,
            "refresh_token": self.refresh_token
        }

        res = requests.post(url, data=data)

        if res.status_code != 200:
            print("❌ refresh_token 갱신 실패", res.text)
            return False

        res_json = res.json()

        self.access_token = res_json.get("access_token", self.access_token)

        if "refresh_token" in res_json:
            self.refresh_token = res_json["refresh_token"]

        print("✅ access_token 갱신 성공")
        self.save_local_token()
        return True

    # -------------------------------
    # 5. TOKEN VALIDATION LOGIC
    # -------------------------------
    def validate_and_refresh_tokens(self):
        print("🔍 토큰 유효성 검사 시작...")

        # 테스트용 simple profile API
        test_url = "https://kapi.kakao.com/v2/user/me"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        res = requests.post(test_url, headers=headers)

        # access_token 정상
        if res.status_code == 200:
            print("✅ access_token 정상")
            return True

        # access_token 만료 → refresh_token으로 갱신
        if res.status_code == 401:
            print("⚠ access_token 만료 → refresh_token 갱신 필요")

            if self.refresh_token:
                ok = self.refresh_access_token()
                if ok:
                    return True
                else:
                    print("❌ refresh_token 갱신 실패 → access_token으로 refresh_token 발급 시도")

        # refresh_token도 잘못되었거나 없는 경우
        print("⚠ refresh_token 없음 또는 무효 → access_token으로 refresh_token 재발급")
        self.issue_refresh_token_via_access()

        return True

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