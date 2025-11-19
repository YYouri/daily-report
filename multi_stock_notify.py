import os
import json
import requests
from datetime import datetime, timedelta
import yfinance as yf
import time

TOKEN_FILE = "kakao_access_token.json"
MAX_RETRY = 3
MAX_MESSAGE_LEN = 900  # 카톡 메시지 안전 길이

class KakaoNotifier:
    def __init__(self):
        self.rest_api_key = os.environ["KAKAO_REST_API_KEY"]
        self.refresh_token = os.environ["KAKAO_REFRESH_TOKEN"]
        self.redirect_uri = os.environ["KAKAO_REDIRECT_URI"]
        self.token_info = {}
        self.load_token()

    def load_token(self):
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r", encoding="utf-8") as f:
                self.token_info = json.load(f)
        else:
            self.refresh_access_token()

    def refresh_access_token(self):
        url = "https://kauth.kakao.com/oauth/token"
        data = {
            "grant_type": "refresh_token",
            "client_id": self.rest_api_key,
            "refresh_token": self.refresh_token,
        }
        try:
            res = requests.post(url, data=data, timeout=10)
            print("토큰 갱신 상태:", res.status_code, res.text)
            res.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"토큰 갱신 실패: {e}")

        res_json = res.json()
        self.token_info["access_token"] = res_json["access_token"]
        self.token_info["expires_at"] = (datetime.now() + timedelta(seconds=res_json.get("expires_in", 3600))).isoformat()
        if "refresh_token" in res_json:
            self.refresh_token = res_json["refresh_token"]

        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump(self.token_info, f, ensure_ascii=False, indent=2)

    def send_message(self, text):
        # 메시지가 너무 길면 나누기
        messages = [text[i:i+MAX_MESSAGE_LEN] for i in range(0, len(text), MAX_MESSAGE_LEN)]

        for msg in messages:
            for attempt in range(1, MAX_RETRY+1):
                try:
                    if not self.token_info.get("access_token"):
                        self.refresh_access_token()

                    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
                    headers = {
                        "Authorization": f"Bearer {self.token_info['access_token']}",
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
                        print("401 Unauthorized → 토큰 갱신 후 재시도")
                        self.refresh_access_token()
                        continue

                    res.raise_for_status()
                    print("카톡 메시지 전송 성공 ✅")
                    break

                except requests.RequestException as e:
                    print(f"전송 실패 시도 {attempt}: {e}")
                    if attempt < MAX_RETRY:
                        time.sleep(2)
                    else:
                        print("최종 실패 ❌")

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
        stock_message = get_stock_info(["AAPL","TSLA","MSFT","GOOG","AMZN"])  # 원하는 종목 추가
        today = datetime.now().strftime("%Y-%m-%d")
        message = f"📊 {today} 주식 정보\n{stock_message}"
        notifier.send_message(message)
    except Exception as e:
        print("스크립트 실행 중 오류:", e)