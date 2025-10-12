# backend/main.py - FastAPI 백엔드 서버 예시
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, date
from typing import List, Optional
import json

app = FastAPI(title="Financial Analyzer API", version="1.0.0")

# CORS 설정 (프론트엔드와 통신 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:5500", "*"],  # 프론트엔드 주소
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 데이터 모델 정의
class Transaction(BaseModel):
    id: Optional[int] = None
    date: str
    amount: float
    category: str
    description: str
    type: str  # 'income' or 'expense'

class FinancialData(BaseModel):
    date: str
    income: float
    expense: float
    transactions: int

class CategoryExpense(BaseModel):
    name: str
    amount: float
    percentage: float

# 임시 데이터 저장소 (실제로는 데이터베이스 사용)
transactions_db = []
next_id = 1

# API 엔드포인트

@app.get("/api/health")
async def health_check():
    """서버 상태 확인"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/financial/date/{target_date}")
async def get_financial_data_by_date(target_date: str):
    """특정 날짜의 재정 데이터 조회"""
    try:
        # 해당 날짜의 거래 내역 필터링
        date_transactions = [t for t in transactions_db if t.get("date") == target_date]
        
        income = sum(t.get("amount", 0) for t in date_transactions if t.get("type") == "income")
        expense = sum(t.get("amount", 0) for t in date_transactions if t.get("type") == "expense")
        
        return {
            "date": target_date,
            "income": income,
            "expense": expense,
            "transactions": len(date_transactions),
            "balance": income - expense
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/financial/period")
async def get_financial_data_by_period(start_date: str, end_date: str):
    """기간별 재정 데이터 조회"""
    try:
        # 기간 내 거래 내역 필터링
        period_transactions = [
            t for t in transactions_db 
            if start_date <= t.get("date", "") <= end_date
        ]
        
        total_income = sum(t.get("amount", 0) for t in period_transactions if t.get("type") == "income")
        total_expense = sum(t.get("amount", 0) for t in period_transactions if t.get("type") == "expense")
        
        return {
            "startDate": start_date,
            "endDate": end_date,
            "totalIncome": total_income,
            "totalExpense": total_expense,
            "totalTransactions": len(period_transactions),
            "balance": total_income - total_expense
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/financial/categories")
async def get_category_expenses(start_date: str, end_date: str):
    """카테고리별 지출 데이터 조회"""
    try:
        # 기간 내 지출 거래만 필터링
        expense_transactions = [
            t for t in transactions_db 
            if start_date <= t.get("date", "") <= end_date and t.get("type") == "expense"
        ]
        
        # 카테고리별 집계
        categories = {}
        total_expense = 0
        
        for transaction in expense_transactions:
            category = transaction.get("category", "기타")
            amount = transaction.get("amount", 0)
            categories[category] = categories.get(category, 0) + amount
            total_expense += amount
        
        # 퍼센트 계산 및 결과 정리
        result = []
        for category, amount in categories.items():
            percentage = (amount / total_expense * 100) if total_expense > 0 else 0
            result.append({
                "name": category,
                "amount": amount,
                "percentage": round(percentage, 1)
            })
        
        return sorted(result, key=lambda x: x["amount"], reverse=True)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/financial/transactions")
async def get_transactions(start_date: str, end_date: str, page: int = 1, limit: int = 50):
    """거래 내역 조회 (페이징 지원)"""
    try:
        # 기간 내 거래 내역 필터링
        filtered_transactions = [
            t for t in transactions_db 
            if start_date <= t.get("date", "") <= end_date
        ]
        
        # 페이징 처리
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_transactions = filtered_transactions[start_idx:end_idx]
        
        return {
            "transactions": paginated_transactions,
            "total": len(filtered_transactions),
            "page": page,
            "limit": limit,
            "totalPages": (len(filtered_transactions) + limit - 1) // limit
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/financial/transactions")
async def add_transaction(transaction: Transaction):
    """새 거래 추가"""
    global next_id
    try:
        transaction_dict = transaction.dict()
        transaction_dict["id"] = next_id
        next_id += 1
        
        transactions_db.append(transaction_dict)
        
        return {"message": "거래가 성공적으로 추가되었습니다.", "transaction": transaction_dict}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/financial/transactions/{transaction_id}")
async def update_transaction(transaction_id: int, transaction: Transaction):
    """거래 수정"""
    try:
        for i, t in enumerate(transactions_db):
            if t.get("id") == transaction_id:
                transaction_dict = transaction.dict()
                transaction_dict["id"] = transaction_id
                transactions_db[i] = transaction_dict
                return {"message": "거래가 성공적으로 수정되었습니다.", "transaction": transaction_dict}
        
        raise HTTPException(status_code=404, detail="거래를 찾을 수 없습니다.")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/financial/transactions/{transaction_id}")
async def delete_transaction(transaction_id: int):
    """거래 삭제"""
    try:
        for i, t in enumerate(transactions_db):
            if t.get("id") == transaction_id:
                deleted_transaction = transactions_db.pop(i)
                return {"message": "거래가 성공적으로 삭제되었습니다.", "transaction": deleted_transaction}
        
        raise HTTPException(status_code=404, detail="거래를 찾을 수 없습니다.")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/financial/dashboard/{period}")
async def get_dashboard_summary(period: str = "month"):
    """대시보드 요약 데이터"""
    try:
        # 간단한 요약 통계 반환
        total_income = sum(t.get("amount", 0) for t in transactions_db if t.get("type") == "income")
        total_expense = sum(t.get("amount", 0) for t in transactions_db if t.get("type") == "expense")
        
        return {
            "period": period,
            "totalIncome": total_income,
            "totalExpense": total_expense,
            "balance": total_income - total_expense,
            "transactionCount": len(transactions_db)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 서버 실행 명령어
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)