# CoupangWishlistDiscordBot
상품 페이지 URL을 입력해두면 가격 변동/품절/재입고시 디스코드로 알려주는 디스코드 봇입니다.

# TODO
* 디스코드 서버 지원

# 사용 방법
* 먼저 의존성을 설치합니다. (requirements.txt 참조)
* 봇을 1회 실행 후 생성된 config.json에 설정 값을 입력합니다.
  - bot_token: 디스코드 봇 토큰
  - user_id: 본인의 (혹은 메시지를 받을 유저의) 유저 ID
  - test_mode: 테스트 모드 활성화 여부 (무엇인지 모르겠다면 False로 냅두세요.)
  - interval: 정보 확인 주기
  - login: 가격을 확인하기 전 로그인 할지 여부 (True로 설정시 email과 pw 값 설정 필요)
  - email/pw: 쿠팡 로그인 이메일 비밀번호 (login 설정 미사용시 불필요)

* 자신의 서버로 봇을 초대하고, 봇을 구동하면 DM이 옵니다. (서버 구성원이 DM을 보내도록 허용한 서버에 봇을 초대해야 됩니다.)
