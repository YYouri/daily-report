카카오 API를 활용하면 카카오톡으로 보내고자 하는 내용의 메시지를 자동 전송 할 수 있다.

1. 카카오에서 제공하는 공식 개발자 포털인 카카오 디벨로퍼스 에 접속해서 앱을 생성한다.
카카오디벨로퍼스 https://developers.kakao.com/

2. 앱생성
앱이름 : 깃헙 연동 앱
회사명 : NONE 

3. 앱 설정 (카카오 로그인, 동의 항목)
생성한 앱을 클릭하면 항목 별 설정이 가능하다.

카카오 로그인 - 사용 설정 ON , 리다이렉트 URI=https://example.com/oauth 추가
동의 항목-접근권한-카카오톡 메시지 전송 (이용 중 동의)

4. 앱설정 -> 앱 -> 일반 클릭
REST API 키(client_id) 를 발급받고, 카카오 API는 액세스 토큰(Access Token)과, 액세스 토큰을 갱신하는 데 쓰는 리프레시 토큰(Refresh Token)이 있다.

*Auth code 발급 방법 
이제 인증 코드(Auth code)를 받아야 한다. 이 코드는 최초 1회만 발급받으면 되고, 이후에는 자동으로 토큰이 갱신된다.
https://kauth.kakao.com/oauth/authorize?client_id=YOUR_REST_API_KEY&redirect_uri=https://example.com/oauth&response_type=code&scope=talk_message
->
카카오 로그인 화면->권한 동의 화면( "카카오톡 메시지 전송" 권한에 동의)->"동의하고 계속하기" 버튼을 클릭 -> https://example.com/oauth?code=인증코드값 

인증코드값 = Auth code 
(인증 코드는 발급받은 후 10분 내에 사용해야한다.)

*REFRESH_TOKEN 발급 방법 
curl -X POST "https://kauth.kakao.com/oauth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "client_id={client_id}" \
  -d "redirect_uri=https://example.com/oauth" \
  -d "code={Auth code}"

참고, 응답 예제)
{"access_token":"yTbcCPIhrC5TyNXYnu9c3y6TBvTWuj_CAAAAAQoXNd0AAAGam1RSVB7SOb8w2j0_",
"token_type":"bearer",
"refresh_token":"YvHYxQTojVOvXTVi2y-Kt6gsvO2otzEGAAAAAgoXNd0AAAGam1RSTh7SOb8w2j0_",
"expires_in":21599,"scope":"talk_message","refresh_token_expires_in":5183999}