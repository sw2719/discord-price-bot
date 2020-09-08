# CoupangWishlistDiscordBot
* coupang_bot
  - 현재 개발 중인 상태로, 상품 페이지 URL을 입력해두면 가격 변동/품절/재입고시 디스코드로 알려주는 디스코드 봇입니다.
* coupang_bot_login
  - 위와 동일하나 쿠팡 이메일 및 비밀번호를 입력하여 찜 목록에 있는 상품을 감지하는 방식입니다.

# TODO
* 품절 상품 감지
* 디스코드 서버 지원
* 봇 명령어를 통한 상품 URL 추가
* 쿠팡 상품 URL 소스코드에서 분리

# 사용 방법
* price_getter

  - 먼저 의존성을 설치합니다. (requirements.txt 참조)
  - 디스코드 봇을 만든 후 price_getter.py의 TOKEN에 토큰을 넣습니다.
  - TARGET_USER에 자신의 유저 ID를 넣습니다.
  - EMAIL과 PW에 각각 쿠팡 이메일, 비밀번호를 넣습니다.
  - 자신의 서버로 봇을 초대하고, 봇을 구동하면 DM이 옵니다. (서버 구성원이 DM을 보내도록 허용한 서버에 봇을 초대해야 됩니다.)

* price_getter_url

  - 먼저 의존성을 설치합니다. (requirements.txt 참조)
  - 디스코드 봇을 만든 후 price_getter.py의 TOKEN에 토큰을 넣습니다.
  - URL_LIST에 가격 알림을 받을 상품 URL을 넣습니다.
  - EMAIL과 PW에 각각 쿠팡 이메일, 비밀번호를 넣습니다.
  - 자신의 서버로 봇을 초대하고, 봇을 구동하면 DM이 옵니다. (서버 구성원이 DM을 보내도록 허용한 서버에 봇을 초대해야 됩니다.)
