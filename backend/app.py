from fastapi import FastAPI, Query
from datetime import date
import uvicorn

app = FastAPI()

    # 예시: /기간조회/?start_date=2025-01-02&end_date=2025-03-03
@app.get("/기간조회/")
def get_articles_by_period(
    start_date: date = Query(..., description="시작 날짜 (YYYY-MM-DD)"),
    end_date: date = Query(..., description="종료 날짜 (YYYY-MM-DD)")
):
    # 실제 DB 조회 로직은 여기에 구현
    return {"start_date": str(start_date), "end_date": str(end_date), "message": "해당 기간의 데이터를 반환합니다."}

# 서버를 직접 실행할 경우 (개발용)
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)