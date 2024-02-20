# Discord Price bot
상품 페이지 URL을 입력해두면 상품 정보 변동시 디스코드로 알려주는 디스코드 봇입니다.

# 사용 방법
* 먼저 의존성을 설치합니다. (requirements.txt 참조)
* 봇을 1회 실행 후 생성된 config.json에 설정 값을 입력합니다.
  - 설정 값 정보 추후 추가 예정
* Discord 개발자 포털의 자신의 봇 설정에서 Privileged Gateway Intents에 있는 Server Members Intent를 켜줘야 제대로 작동합니다.
* 자신의 서버로 봇을 초대하고, 봇을 구동하면 DM이 옵니다. (서버 구성원이 DM을 보내도록 허용한 서버에 봇을 초대해야 됩니다.)

# 주의 사항
* 사이트 로그인 설정을 사용할 시 계정이름과 비밀번호를 설정 파일에 평문으로 저장해야 하므로 개인정보 유출이 우려된다면 사용하지 마세요.
* 설정한 주기마다 상품 정보가 업데이트되는 것을 보장하지 않습니다.
  - 주기마다 상품 정보가 업데이트 되는 것이 아닌, 상품 정보가 모두 업데이트 된 이후 설정한 주기만큼 대기합니다.

# 현재 지원 사이트
* 쿠팡
* 다나와
* 네이버 쇼핑[^1]
* 11번가 (11마존)[^1]
* 학생복지스토어[^2]

[^1]: 해당 사이트 로드에는 JavaScript가 필요해서 Playwright를 사용하므로 Raspberry Pi와 같은 하드웨어에서 동작 시 속도가 느릴 수 있습니다.
[^2]: 상품 가격 및 재고 정보를 불러올려면 로그인 정보가 필요합니다.

