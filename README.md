# CoupangWishlistDiscordBot
price_getter 는 찜 목록에 있는 상품들의 가격이 변동되면 디스코드 DM으로 알려주고, price_getter_url은 직접 가격 알림을 받을 상품 URL을 입력하는 방식입니다. 둘 다 Work-in-progress 입니다.
* 경고: 테스트 결과 봇에서 쿠팡에 로그인하면 PC에서는 로그인이 풀렸습니다. 모바일은 모르겠습니다.

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
