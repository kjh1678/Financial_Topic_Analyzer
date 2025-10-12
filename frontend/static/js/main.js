// 메인 애플리케이션 초기화
document.addEventListener('DOMContentLoaded', function() {
    // 캘린더와 기간 선택자 초기화
    calendar = new Calendar();
    periodSelector = new PeriodSelector();
    
    // 이벤트 리스너 등록
    setupEventListeners();
    
    // 초기 데이터 로드
    initializeApp();
});

// 이벤트 리스너 설정
function setupEventListeners() {
    // 날짜 선택 이벤트
    window.addEventListener('dateSelected', function(event) {
        const selectedDate = event.detail.date;
        const formattedDate = event.detail.formattedDate;
        
        console.log('날짜 선택됨:', formattedDate);
        
        // 선택된 날짜에 따른 추가 처리
        handleDateSelection(selectedDate, formattedDate);
    });

    // 기간 선택 이벤트
    window.addEventListener('periodSelected', function(event) {
        const periodInfo = event.detail;
        
        console.log('기간 선택됨:', periodInfo);
        
        // 선택된 기간에 따른 추가 처리
        handlePeriodSelection(periodInfo);
    });

    // 윈도우 리사이즈 이벤트
    window.addEventListener('resize', function() {
        // 반응형 레이아웃 조정
        handleWindowResize();
    });
}

// 애플리케이션 초기화 (API 연동)
async function initializeApp() {
    try {
        // 서버 연결 테스트
        const isConnected = await financialAPI.testConnection();
        
        if (isConnected) {
            console.log('✅ API 서버 연결 성공');
            showSuccessMessage('서버에 연결되었습니다.', 2000);
        } else {
            console.warn('⚠️ API 서버 연결 실패 - 오프라인 모드로 실행');
            showWarningMessage('서버에 연결할 수 없습니다. 데모 모드로 실행됩니다.', 3000);
        }
        
        // 현재 날짜로 초기 설정
        const today = new Date();
        
        // 대시보드 요약 데이터 로드
        try {
            const dashboardData = await financialAPI.getDashboardSummary();
            updateDashboardSummary(dashboardData);
        } catch (error) {
            console.warn('대시보드 데이터 로드 실패:', error.message);
        }
        
        // 분석 결과 영역 초기화
        updateAnalysisSection({
            period: 'today',
            startDate: today,
            endDate: today,
            text: '오늘'
        });
        
    } catch (error) {
        console.error('앱 초기화 에러:', error);
        showErrorMessage('애플리케이션 초기화 중 오류가 발생했습니다.');
    }
}

// 날짜 선택 처리
function handleDateSelection(selectedDate, formattedDate) {
    // 선택된 날짜에 대한 데이터 분석 수행
    performDateAnalysis(selectedDate);
    
    // UI 업데이트
    updateSelectedDateDisplay(formattedDate);
}

// 기간 선택 처리
function handlePeriodSelection(periodInfo) {
    // 선택된 기간에 대한 데이터 분석 수행
    performPeriodAnalysis(periodInfo);
    
    // 분석 결과 영역 업데이트
    updateAnalysisSection(periodInfo);
}

// 날짜 분석 수행 (API 연동)
async function performDateAnalysis(selectedDate) {
    console.log('날짜 분석 수행:', selectedDate);
    
    try {
        // 로딩 상태 표시
        showLoadingState('날짜별 데이터를 불러오는 중...');
        
        // API를 통해 실제 데이터 조회
        const analysisData = await financialAPI.getFinancialDataByDate(selectedDate);
        
        // 데이터가 없을 경우 기본값 설정
        if (!analysisData || Object.keys(analysisData).length === 0) {
            analysisData = {
                date: selectedDate,
                income: 0,
                expense: 0,
                transactions: 0,
                message: '해당 날짜에 대한 데이터가 없습니다.'
            };
        }
        
        displayDateAnalysis(analysisData);
        hideLoadingState();
        
    } catch (error) {
        console.error('날짜 분석 API 에러:', error);
        hideLoadingState();
        
        // 서버 연결 실패 시 임시 데이터 또는 에러 메시지 표시
        if (!financialAPI.isOnline()) {
            showErrorMessage('인터넷 연결을 확인해주세요.');
        } else {
            // 개발 중에는 임시 데이터로 대체
            const fallbackData = {
                date: selectedDate,
                income: Math.floor(Math.random() * 100000),
                expense: Math.floor(Math.random() * 80000),
                transactions: Math.floor(Math.random() * 20) + 1,
                isDemo: true
            };
            displayDateAnalysis(fallbackData);
            showWarningMessage('서버에 연결할 수 없어 데모 데이터를 표시합니다.');
        }
    }
}

// 기간 분석 수행 (API 연동)
async function performPeriodAnalysis(periodInfo) {
    console.log('기간 분석 수행:', periodInfo);
    
    try {
        // 로딩 상태 표시
        showLoadingState('기간별 데이터를 불러오는 중...');
        
        // API를 통해 실제 데이터 조회
        const [financialData, categoryData] = await Promise.all([
            financialAPI.getFinancialDataByPeriod(periodInfo.startDate, periodInfo.endDate),
            financialAPI.getCategoryExpenses(periodInfo.startDate, periodInfo.endDate)
        ]);
        
        // 데이터 통합 및 가공
        const analysisData = {
            period: periodInfo.period,
            startDate: periodInfo.startDate,
            endDate: periodInfo.endDate,
            totalIncome: financialData?.totalIncome || 0,
            totalExpense: financialData?.totalExpense || 0,
            totalTransactions: financialData?.totalTransactions || 0,
            categories: categoryData || [],
            rawData: financialData
        };
        
        // 카테고리 데이터가 없을 경우 기본값 생성
        if (!analysisData.categories.length) {
            analysisData.categories = generateDefaultCategories();
            analysisData.isDemo = true;
        }
        
        displayPeriodAnalysis(analysisData);
        hideLoadingState();
        
    } catch (error) {
        console.error('기간 분석 API 에러:', error);
        hideLoadingState();
        
        // 서버 연결 실패 시 처리
        if (!financialAPI.isOnline()) {
            showErrorMessage('인터넷 연결을 확인해주세요.');
        } else {
            // 개발 중에는 임시 데이터로 대체
            const fallbackData = {
                period: periodInfo.period,
                startDate: periodInfo.startDate,
                endDate: periodInfo.endDate,
                totalIncome: Math.floor(Math.random() * 1000000),
                totalExpense: Math.floor(Math.random() * 800000),
                totalTransactions: Math.floor(Math.random() * 200) + 10,
                categories: generateRandomCategories(),
                isDemo: true
            };
            displayPeriodAnalysis(fallbackData);
            showWarningMessage('서버에 연결할 수 없어 데모 데이터를 표시합니다.');
        }
    }
}

// 임시 카테고리 데이터 생성 (API 데이터가 없을 때 사용)
function generateRandomCategories() {
    const categories = [
        '식료품', '교통비', '의료비', '문화생활', '쇼핑', '외식', '공과금', '통신비'
    ];
    
    return categories.map(category => ({
        name: category,
        amount: Math.floor(Math.random() * 100000),
        percentage: Math.floor(Math.random() * 30) + 5
    }));
}

// 기본 카테고리 데이터 생성
function generateDefaultCategories() {
    return [
        { name: '데이터 없음', amount: 0, percentage: 0 }
    ];
}

// 날짜 분석 결과 표시
function displayDateAnalysis(data) {
    const analysisSection = document.querySelector('.analysis-section');
    const placeholder = analysisSection.querySelector('.analysis-placeholder');
    
    const demoIndicator = data.isDemo ? '<span class="demo-indicator">DEMO</span>' : '';
    const messageDisplay = data.message ? `<p class="no-data-message">${data.message}</p>` : '';
    
    const analysisHTML = `
        <div class="date-analysis">
            <h4>${formatDateKorean(data.date)} 분석 결과${demoIndicator}</h4>
            ${messageDisplay}
            <div class="analysis-summary">
                <div class="summary-item">
                    <span class="label">수입:</span>
                    <span class="value income">${formatCurrency(data.income)}</span>
                </div>
                <div class="summary-item">
                    <span class="label">지출:</span>
                    <span class="value expense">${formatCurrency(data.expense)}</span>
                </div>
                <div class="summary-item">
                    <span class="label">순수익:</span>
                    <span class="value ${data.income - data.expense >= 0 ? 'profit' : 'loss'}">
                        ${formatCurrency(data.income - data.expense)}
                    </span>
                </div>
                <div class="summary-item">
                    <span class="label">거래 건수:</span>
                    <span class="value">${data.transactions}건</span>
                </div>
            </div>
        </div>
    `;
    
    placeholder.innerHTML = analysisHTML;
}

// 기간 분석 결과 표시
function displayPeriodAnalysis(data) {
    const analysisSection = document.querySelector('.analysis-section');
    const placeholder = analysisSection.querySelector('.analysis-placeholder');
    
    const demoIndicator = data.isDemo ? '<span class="demo-indicator">DEMO</span>' : '';
    
    const categoriesHTML = data.categories
        .sort((a, b) => b.amount - a.amount)
        .slice(0, 5)
        .map(category => `
            <div class="category-item">
                <span class="category-name">${category.name}</span>
                <span class="category-amount">${formatCurrency(category.amount)}</span>
                <span class="category-percentage">${category.percentage}%</span>
            </div>
        `).join('');
    
    const analysisHTML = `
        <div class="period-analysis">
            <h4>${data.period === 'custom' ? '선택 기간' : getPeriodKoreanName(data.period)} 분석 결과${demoIndicator}</h4>
            <div class="period-range">
                ${formatDateKorean(data.startDate)} ~ ${formatDateKorean(data.endDate)}
            </div>
            <div class="analysis-summary">
                <div class="summary-item">
                    <span class="label">총 수입:</span>
                    <span class="value income">${formatCurrency(data.totalIncome)}</span>
                </div>
                <div class="summary-item">
                    <span class="label">총 지출:</span>
                    <span class="value expense">${formatCurrency(data.totalExpense)}</span>
                </div>
                <div class="summary-item">
                    <span class="label">순수익:</span>
                    <span class="value ${data.totalIncome - data.totalExpense >= 0 ? 'profit' : 'loss'}">
                        ${formatCurrency(data.totalIncome - data.totalExpense)}
                    </span>
                </div>
                <div class="summary-item">
                    <span class="label">총 거래 건수:</span>
                    <span class="value">${data.totalTransactions}건</span>
                </div>
            </div>
            <div class="top-categories">
                <h5>주요 지출 카테고리</h5>
                <div class="categories-list">
                    ${categoriesHTML || '<p class="no-categories">카테고리 데이터가 없습니다.</p>'}
                </div>
            </div>
        </div>
    `;
    
    placeholder.innerHTML = analysisHTML;
}

// 분석 결과 영역 업데이트
function updateAnalysisSection(periodInfo) {
    // 기간 정보에 따른 분석 수행
    performPeriodAnalysis(periodInfo);
}

// 선택된 날짜 표시 업데이트
function updateSelectedDateDisplay(formattedDate) {
    // 필요시 추가 UI 업데이트
}

// 윈도우 리사이즈 처리
function handleWindowResize() {
    // 캘린더 재계산 (필요시)
    if (window.calendar) {
        calendar.generateCalendar();
    }
}

// 환영 메시지 표시
function showWelcomeMessage() {
    console.log('Financial Analyzer가 초기화되었습니다.');
}

// 로딩 상태 표시
function showLoadingState(message = '데이터를 불러오는 중...') {
    const analysisSection = document.querySelector('.analysis-section');
    const placeholder = analysisSection.querySelector('.analysis-placeholder');
    
    placeholder.innerHTML = `
        <div class="loading-state">
            <div class="spinner"></div>
            <p>${message}</p>
        </div>
    `;
}

// 로딩 상태 숨김
function hideLoadingState() {
    // 로딩 상태는 실제 데이터로 교체되므로 별도 처리 불필요
}

// 성공 메시지 표시
function showSuccessMessage(message, duration = 3000) {
    showToast(message, 'success', duration);
}

// 경고 메시지 표시
function showWarningMessage(message, duration = 5000) {
    showToast(message, 'warning', duration);
}

// 에러 메시지 표시
function showErrorMessage(message, duration = 5000) {
    showToast(message, 'error', duration);
}

// 토스트 메시지 표시
function showToast(message, type = 'info', duration = 3000) {
    // 기존 토스트 제거
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }
    
    // 새 토스트 생성
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-content">
            <span class="toast-icon">${getToastIcon(type)}</span>
            <span class="toast-message">${message}</span>
            <button class="toast-close" onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
    `;
    
    document.body.appendChild(toast);
    
    // 애니메이션 적용
    setTimeout(() => toast.classList.add('show'), 100);
    
    // 자동 제거
    if (duration > 0) {
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
}

// 토스트 아이콘 반환
function getToastIcon(type) {
    const icons = {
        success: '✅',
        warning: '⚠️',
        error: '❌',
        info: 'ℹ️'
    };
    return icons[type] || icons.info;
}

// 대시보드 요약 데이터 업데이트
function updateDashboardSummary(dashboardData) {
    if (!dashboardData) return;
    
    console.log('대시보드 데이터 업데이트:', dashboardData);
    // 향후 대시보드 UI 구현 시 사용
}

// 유틸리티 함수들
function formatCurrency(amount) {
    return new Intl.NumberFormat('ko-KR', {
        style: 'currency',
        currency: 'KRW'
    }).format(amount);
}

function formatDateKorean(date) {
    return new Intl.DateTimeFormat('ko-KR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    }).format(date);
}

function getPeriodKoreanName(period) {
    const periodNames = {
        'today': '오늘',
        'week': '1주일',
        'month': '1개월',
        'quarter': '3개월',
        'half-year': '6개월',
        'nine-months': '9개월',
        'year': '1년'
    };
    
    return periodNames[period] || period;
}

// 추가 CSS 스타일을 동적으로 추가
function addAnalysisStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .analysis-summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        
        .summary-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #3498db;
        }
        
        .summary-item .label {
            font-weight: 600;
            color: #555;
        }
        
        .summary-item .value {
            font-weight: 700;
        }
        
        .value.income {
            color: #27ae60;
        }
        
        .value.expense {
            color: #e74c3c;
        }
        
        .value.profit {
            color: #27ae60;
        }
        
        .value.loss {
            color: #e74c3c;
        }
        
        .period-range {
            text-align: center;
            color: #666;
            margin-bottom: 15px;
            font-size: 0.9rem;
        }
        
        .top-categories h5 {
            margin: 20px 0 10px 0;
            color: #2c3e50;
        }
        
        .categories-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        
        .category-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            background: #f8f9fa;
            border-radius: 6px;
            font-size: 0.9rem;
        }
        
        .category-name {
            flex: 1;
            font-weight: 500;
        }
        
        .category-amount {
            color: #e74c3c;
            font-weight: 600;
            margin-right: 10px;
        }
        
        .category-percentage {
            color: #666;
            font-size: 0.8rem;
        }
        
        /* 로딩 스피너 */
        .loading-state {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 40px;
            color: #666;
        }
        
        .spinner {
            width: 40px;
            height: 40px;
            border: 4px solid #f3f3f3;
            border-top: 4px solid #3498db;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-bottom: 15px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        /* 토스트 메시지 */
        .toast {
            position: fixed;
            top: 20px;
            right: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            z-index: 1000;
            opacity: 0;
            transform: translateX(100%);
            transition: all 0.3s ease;
            max-width: 400px;
            min-width: 300px;
        }
        
        .toast.show {
            opacity: 1;
            transform: translateX(0);
        }
        
        .toast-content {
            display: flex;
            align-items: center;
            padding: 15px;
            gap: 10px;
        }
        
        .toast-icon {
            font-size: 1.2rem;
            flex-shrink: 0;
        }
        
        .toast-message {
            flex: 1;
            font-weight: 500;
            color: #333;
        }
        
        .toast-close {
            background: none;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            color: #999;
            padding: 0;
            width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .toast-close:hover {
            color: #666;
        }
        
        .toast-success {
            border-left: 4px solid #27ae60;
        }
        
        .toast-warning {
            border-left: 4px solid #f39c12;
        }
        
        .toast-error {
            border-left: 4px solid #e74c3c;
        }
        
        .toast-info {
            border-left: 4px solid #3498db;
        }
        
        /* 데모 데이터 표시 */
        .demo-indicator {
            display: inline-block;
            background: #f39c12;
            color: white;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 600;
            margin-left: 8px;
        }
        
        /* 반응형 토스트 */
        @media (max-width: 480px) {
            .toast {
                right: 10px;
                left: 10px;
                max-width: none;
                min-width: auto;
            }
        }
    `;
    
    document.head.appendChild(style);
}

// 페이지 로드 완료 후 추가 스타일 적용
document.addEventListener('DOMContentLoaded', function() {
    addAnalysisStyles();
});