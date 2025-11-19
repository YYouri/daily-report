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
        self.rest_api_key = os.environ["KAKAO_REST_API_KEY"]
        self.redirect_uri = os.environ["KAKAO_REDIRECT_URI"]
        self.access_token = os.environ["KAKAO_ACCESS_TOKEN"]
        self.refresh_token = os.environ.get("KAKAO_REFRESH_TOKEN", "")
        self.token_info = {}
        self.load_token()

    def load_token(self):
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r", encoding="utf-8") as f:
                self.token_info = json.load(f)
                self.access_token = self.token_info.get("access_token", self.access_token)
                self.refresh_token = self.token_info.get("refresh_token", self.refresh_token)
        else:
            # 최초 실행, refresh_token이 없으면 access_token으로 발급 시도
            if not self.refresh_token:
                print("🚀 최초 실행: access_token으로 refresh_token 발급 시도")
                self.obtain_refresh_token()

    def save_token(self):
        self.token_info["access_token"] = self.access_token
        self.token_info["refresh_token"] = self.refresh_token
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump(self.token_info, f, ensure_ascii=False, indent=2)

    def obtain_refresh_token(self):
        # 카카오 API에선 refresh_token은 access_token 발급 시 같이 내려옴
        # 여기서는 access_token으로 refresh_token 발급 시도 (grant_type=refresh_token)
        if not self.refresh_token:
            url = "https://kauth.kakao.com/oauth/token"
            data = {
                "grant_type": "refresh_token",
                "client_id": self.rest_api_key,
                "refresh_token": "",
            }
            try:
                res = requests.post(url, data=data, timeout=10)
                print("refresh_token 발급 시도 상태:", res.status_code, res.text)
                if res.status_code == 200:
                    res_json = res.json()
                    self.refresh_token = res_json.get("refresh_token", "")
                    self.access_token = res_json.get("access_token", self.access_token)
                    self.save_token()
                    print("✅ refresh_token 발급 성공")
                else:
                    print("❌ refresh_token 발급 실패, 수동 갱신 필요")
            except Exception as e:
                print("refresh_token 발급 중 오류:", e)

    def refresh_access_token(self):
        if not self.refresh_token:
            print("❌ refresh_token 없음 → 수동 발급 필요")
            return False
        url = "https://kauth.kakao.com/oauth/token"
        data = {
            "grant_type": "refresh_token",
            "client_id": self.rest_api_key,
            "refresh_token": self.refresh_token,
        }
        try:
            res = requests.post(url, data=data, timeout=10)
            print("access_token 갱신 상태:", res.status_code, res.text)
            res.raise_for_status()
            res_json = res.json()
            self.access_token = res_json.get("access_token", self.access_token)
            self.save_token()
            return True
        except Exception as e:
            print("access_token 갱신 실패:", e)
            return False

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