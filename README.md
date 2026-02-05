# Steam Library AI Manager

Steam API와 Google Gemini API를 활용한 게임 라이브러리 정리 및 추천 서비스입니다.

## 주요 기능
- 🎮 **Steam 라이브러리 연동**: 사용자의 모든 게임 목록을 자동으로 가져옵니다.
- 🤖 **AI 자동 분류**: Gemini AI가 게임의 장르, 플레이 스타일, 분위기를 분석합니다.
- 📊 **통계 대시보드**: 플레이 타임, 장르별 분포 등을 시각적으로 보여줍니다.
- 💬 **AI 추천**: "오늘 뭐 하지?"와 같은 질문에 대해 내 라이브러리를 기반으로 추천해줍니다.

## 설치 방법

1. 저장소 클론
   ```bash
   git clone <repository-url>
   cd steam-library-manager
   ```

2. 가상환경 생성 및 패키지 설치
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. 환경 변수 설정
   `.env.example` 파일을 `.env`로 복사하고 키를 입력하세요.
   ```bash
   cp .env.example .env
   ```
   - `STEAM_API_KEY`: [Steam Dev Portal](https://steamcommunity.com/dev/apikey)에서 발급
   - `GEMINI_API_KEY`: [Google AI Studio](https://makersuite.google.com/app/apikey)에서 발급
   - `STEAM_ID`: 본인의 Steam ID 17자리 (선택 사항)

## 실행 방법

```bash
streamlit run app.py
```

## 배포 (Railway)

1. GitHub에 코드를 푸시합니다.
2. Railway에서 새 프로젝트를 생성하고 GitHub 레포지토리를 연결합니다.
3. Railway 대시보드의 **Variables** 탭에서 `STEAM_API_KEY`와 `GEMINI_API_KEY`를 설정합니다.
4. 배포가 완료되면 제공된 도메인으로 접속합니다.

## 기술 스택
- Python 3.9+
- Streamlit
- LangChain
- Google Gemini API
- Steam Web API
