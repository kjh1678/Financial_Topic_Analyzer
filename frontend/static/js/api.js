// API 통신 관리 클래스
class FinancialAPI {
    constructor() {
        // API 기본 설정 - 환경에 따라 자동 설정
        this.baseURL = this.getBaseURL();
        this.defaultHeaders = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        };
        this.timeout = 10000; // 10초 타임아웃
    }

    // 환경에 따른 API URL 자동 설정
    getBaseURL() {
        // 환경 변수나 설정 파일에서 읽어올 수도 있음
        const host = window.location.hostname;
        const protocol = window.location.protocol;
        
        // 개발 환경 감지
        if (host === 'localhost' || host === '127.0.0.1' || host.includes('192.168.')) {
            return 'http://localhost:8000/api';
        }
        
        // 프로덕션 환경
        if (host.includes('your-domain.com')) {
            return 'https://api.your-domain.com/api';
        }
        
        // 스테이징 환경
        if (host.includes('staging')) {
            return 'https://staging-api.your-domain.com/api';
        }
        
        // 기본값 (개발 환경)
        return 'http://localhost:8000/api';
    }

    // 기본 fetch 요청 래퍼
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        
        const config = {
            method: 'GET',
            headers: { ...this.defaultHeaders, ...options.headers },
            ...options
        };

        // 타임아웃 설정
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);
        config.signal = controller.signal;

        try {
            console.log(`API 요청: ${config.method} ${url}`);
            
            const response = await fetch(url, config);
            clearTimeout(timeoutId);

            // HTTP 에러 체크
            if (!response.ok) {
                throw new Error(`HTTP Error: ${response.status} ${response.statusText}`);
            }

            // Content-Type 체크
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                const data = await response.json();
                console.log(`API 응답 성공: ${url}`, data);
                return data;
            } else {
                const text = await response.text();
                console.log(`API 응답 (텍스트): ${url}`, text);
                return text;
            }

        } catch (error) {
            clearTimeout(timeoutId);
            
            if (error.name === 'AbortError') {
                throw new Error('요청 시간이 초과되었습니다.');
            }
            
            console.error(`API 에러: ${url}`, error);
            throw error;
        }
    }

    // GET 요청
    async get(endpoint, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const url = queryString ? `${endpoint}?${queryString}` : endpoint;
        
        return this.request(url, { method: 'GET' });
    }

    // POST 요청
    async post(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    // PUT 요청
    async put(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    // DELETE 요청
    async delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }

    // 날짜별 재정 데이터 조회
    async getFinancialDataByDate(date) {
        const formattedDate = this.formatDateForAPI(date);
        return this.get(`/financial/date/${formattedDate}`);
    }

    // 기간별 재정 데이터 조회
    async getFinancialDataByPeriod(startDate, endDate) {
        const params = {
            start_date: this.formatDateForAPI(startDate),
            end_date: this.formatDateForAPI(endDate)
        };
        return this.get('/financial/period', params);
    }

    // 카테고리별 지출 데이터 조회
    async getCategoryExpenses(startDate, endDate) {
        const params = {
            start_date: this.formatDateForAPI(startDate),
            end_date: this.formatDateForAPI(endDate)
        };
        return this.get('/financial/categories', params);
    }

    // 월별 통계 데이터 조회
    async getMonthlyStatistics(year, month) {
        return this.get(`/financial/monthly/${year}/${month}`);
    }

    // 거래 내역 조회
    async getTransactions(startDate, endDate, page = 1, limit = 50) {
        const params = {
            start_date: this.formatDateForAPI(startDate),
            end_date: this.formatDateForAPI(endDate),
            page: page,
            limit: limit
        };
        return this.get('/financial/transactions', params);
    }

    // 새 거래 추가
    async addTransaction(transactionData) {
        const data = {
            date: this.formatDateForAPI(transactionData.date),
            amount: transactionData.amount,
            category: transactionData.category,
            description: transactionData.description,
            type: transactionData.type // 'income' or 'expense'
        };
        return this.post('/financial/transactions', data);
    }

    // 거래 수정
    async updateTransaction(transactionId, transactionData) {
        const data = {
            date: this.formatDateForAPI(transactionData.date),
            amount: transactionData.amount,
            category: transactionData.category,
            description: transactionData.description,
            type: transactionData.type
        };
        return this.put(`/financial/transactions/${transactionId}`, data);
    }

    // 거래 삭제
    async deleteTransaction(transactionId) {
        return this.delete(`/financial/transactions/${transactionId}`);
    }

    // 예산 설정 조회
    async getBudget(year, month) {
        return this.get(`/financial/budget/${year}/${month}`);
    }

    // 예산 설정
    async setBudget(year, month, budgetData) {
        return this.post(`/financial/budget/${year}/${month}`, budgetData);
    }

    // 대시보드 요약 데이터 조회
    async getDashboardSummary(period = 'month') {
        return this.get(`/financial/dashboard/${period}`);
    }

    // 재정 목표 조회
    async getFinancialGoals() {
        return this.get('/financial/goals');
    }

    // 재정 목표 설정
    async setFinancialGoal(goalData) {
        return this.post('/financial/goals', goalData);
    }

    // 리포트 생성
    async generateReport(startDate, endDate, reportType = 'summary') {
        const params = {
            start_date: this.formatDateForAPI(startDate),
            end_date: this.formatDateForAPI(endDate),
            type: reportType
        };
        return this.get('/financial/reports', params);
    }

    // 데이터 내보내기
    async exportData(startDate, endDate, format = 'csv') {
        const params = {
            start_date: this.formatDateForAPI(startDate),
            end_date: this.formatDateForAPI(endDate),
            format: format
        };
        
        return this.request('/financial/export', {
            method: 'GET',
            headers: {
                ...this.defaultHeaders,
                'Accept': format === 'csv' ? 'text/csv' : 'application/json'
            }
        });
    }

    // 서버 상태 확인
    async checkServerHealth() {
        try {
            const response = await this.get('/health');
            return { status: 'healthy', data: response };
        } catch (error) {
            return { status: 'unhealthy', error: error.message };
        }
    }

    // 사용자 인증 (향후 확장용)
    async authenticate(credentials) {
        try {
            const response = await this.post('/auth/login', credentials);
            if (response.token) {
                this.setAuthToken(response.token);
            }
            return response;
        } catch (error) {
            throw new Error('인증에 실패했습니다: ' + error.message);
        }
    }

    // 인증 토큰 설정
    setAuthToken(token) {
        this.defaultHeaders['Authorization'] = `Bearer ${token}`;
        localStorage.setItem('auth_token', token);
    }

    // 인증 토큰 제거
    removeAuthToken() {
        delete this.defaultHeaders['Authorization'];
        localStorage.removeItem('auth_token');
    }

    // 저장된 토큰 로드
    loadStoredToken() {
        const token = localStorage.getItem('auth_token');
        if (token) {
            this.setAuthToken(token);
        }
    }

    // 날짜를 API 형식으로 변환
    formatDateForAPI(date) {
        if (typeof date === 'string') {
            return date;
        }
        
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    // API 응답에서 날짜 파싱
    parseAPIDate(dateString) {
        return new Date(dateString);
    }

    // 연결 테스트 (개선된 버전)
    async testConnection() {
        try {
            console.log(`🔍 서버 연결 테스트 중... (${this.baseURL})`);
            
            const health = await this.checkServerHealth();
            if (health.status === 'healthy') {
                console.log('✅ 서버 연결 성공:', health.data);
                return true;
            } else {
                console.warn('⚠️ 서버 연결 불안정:', health.error);
                return false;
            }
        } catch (error) {
            console.error('❌ 서버 연결 실패:', error.message);
            
            // 연결 실패 원인 분석
            if (error.message.includes('fetch')) {
                console.error('   → 네트워크 연결 문제 또는 서버가 실행되지 않음');
                console.error('   → 백엔드 서버가 http://localhost:8000 에서 실행 중인지 확인하세요');
            } else if (error.message.includes('CORS')) {
                console.error('   → CORS 정책 문제');
                console.error('   → 백엔드 서버에서 CORS 설정을 확인하세요');
            }
            
            return false;
        }
    }

    // 오프라인 모드 감지
    isOnline() {
        return navigator.onLine;
    }

    // 재시도 로직이 포함된 요청
    async requestWithRetry(endpoint, options = {}, maxRetries = 3) {
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                return await this.request(endpoint, options);
            } catch (error) {
                console.warn(`API 요청 시도 ${attempt}/${maxRetries} 실패:`, error.message);
                
                if (attempt === maxRetries) {
                    throw error;
                }
                
                // 재시도 전 대기 (지수 백오프)
                const delay = Math.min(1000 * Math.pow(2, attempt - 1), 5000);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    }
}

// 싱글톤 패턴으로 API 인스턴스 생성
const financialAPI = new FinancialAPI();

// 페이지 로드 시 저장된 토큰 로드
document.addEventListener('DOMContentLoaded', () => {
    financialAPI.loadStoredToken();
});

// 전역 사용을 위한 export
window.financialAPI = financialAPI;