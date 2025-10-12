# Financial Analyzer 백엔드 연결 가이드

## 🚀 백엔드 서버 실행 방법

### 1. Python 환경 설정
```bash
# Python 3.8+ 설치 확인
python --version

# 가상환경 생성 (선택사항)
python -m venv financial_analyzer_env

# 가상환경 활성화
# Windows:
financial_analyzer_env\Scripts\activate
# macOS/Linux:
source financial_analyzer_env/bin/activate
```

### 2. 의존성 설치
```bash
# 프로젝트 루트 디렉토리에서
pip install -r requirements.txt
```

### 3. 백엔드 서버 실행
```bash
# backend 폴더에서
cd backend
python main.py

# 또는 uvicorn 직접 실행
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 서버 확인
브라우저에서 다음 URL 접속:
- API 문서: http://localhost:8000/docs
- 서버 상태: http://localhost:8000/api/health

## 🔧 프론트엔드 실행 방법

### 방법 1: Live Server (VS Code 확장)
1. VS Code에서 Live Server 확장 설치
2. index.html 우클릭 → "Open with Live Server"
3. 자동으로 http://127.0.0.1:5500 에서 실행

### 방법 2: Python 간단 서버
```bash
# frontend 폴더에서
cd frontend
python -m http.server 3000
# http://localhost:3000 에서 접속
```

### 방법 3: Node.js 서버
```bash
# frontend 폴더에서
npx http-server -p 3000 -c-1
# http://localhost:3000 에서 접속
```

## 🌐 CORS 문제 해결

백엔드 main.py에서 CORS 설정 확인:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:5500", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 🔍 연결 테스트 방법

### 1. 브라우저 개발자 도구에서 확인
1. F12로 개발자 도구 열기
2. Console 탭에서 다음 메시지 확인:
   - "✅ API 서버 연결 성공" → 정상 연결
   - "❌ 서버 연결 실패" → 연결 문제

### 2. 수동 API 테스트
```javascript
// 브라우저 콘솔에서 직접 테스트
fetch('http://localhost:8000/api/health')
  .then(response => response.json())
  .then(data => console.log('서버 응답:', data))
  .catch(error => console.error('연결 실패:', error));
```

### 3. 브라우저에서 직접 접속
- http://localhost:8000/api/health

## 🔧 문제 해결

### 서버 연결 실패 시
1. **백엔드 서버가 실행 중인지 확인**
   ```bash
   # 포트 8000 사용 중인지 확인
   netstat -ano | findstr :8000
   ```

2. **방화벽 설정 확인**
   - Windows Defender 방화벽에서 Python/포트 8000 허용

3. **CORS 에러 시**
   - 백엔드 CORS 설정에 프론트엔드 주소 추가
   - 브라우저 CORS 확장 프로그램 사용 (개발 시에만)

### API 응답 포맷 확인
예상 응답 형태:
```json
{
  "date": "2024-09-22",
  "income": 100000,
  "expense": 80000,
  "transactions": 5,
  "balance": 20000
}
```

## 🚀 배포 시 고려사항

### 프로덕션 환경
1. **HTTPS 사용**
2. **환경 변수로 API URL 관리**
3. **실제 데이터베이스 연결** (PostgreSQL, MySQL 등)
4. **인증/권한 시스템 구현**
5. **로그 시스템 구축**

### 보안 고려사항
1. API 키 관리
2. 입력값 검증
3. SQL 인젝션 방지
4. 속도 제한 (Rate Limiting)

이 가이드를 따라하시면 프론트엔드와 백엔드가 성공적으로 연결됩니다! 🎉