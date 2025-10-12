// 기간 선택 관리 클래스
class PeriodSelector {
    constructor() {
        this.currentPeriod = 'today';
        this.customStartDate = null;
        this.customEndDate = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.updateSelectedPeriod('today');
    }

    // 이벤트 바인딩
    bindEvents() {
        // 기간 버튼 클릭 이벤트
        document.querySelectorAll('.period-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const period = e.target.dataset.period;
                this.selectPeriod(period);
            });
        });

        // 직접설정 관련 이벤트
        document.getElementById('applyCustomPeriod').addEventListener('click', () => {
            this.applyCustomPeriod();
        });

        document.getElementById('cancelCustomPeriod').addEventListener('click', () => {
            this.cancelCustomPeriod();
        });

        // 날짜 입력 이벤트
        document.getElementById('startDate').addEventListener('change', () => {
            this.validateDateInputs();
        });

        document.getElementById('endDate').addEventListener('change', () => {
            this.validateDateInputs();
        });
    }

    // 기간 선택
    selectPeriod(period) {
        // 모든 버튼에서 active 클래스 제거
        document.querySelectorAll('.period-btn').forEach(btn => {
            btn.classList.remove('active');
        });

        // 선택된 버튼에 active 클래스 추가
        document.querySelector(`[data-period="${period}"]`).classList.add('active');

        this.currentPeriod = period;

        if (period === 'custom') {
            this.showCustomPanel();
        } else {
            this.hideCustomPanel();
            this.updateSelectedPeriod(period);
        }
    }

    // 직접설정 패널 표시
    showCustomPanel() {
        const panel = document.getElementById('customPeriodPanel');
        panel.classList.add('active');
        
        // 현재 날짜로 기본값 설정
        const today = new Date();
        const todayStr = this.formatDateForInput(today);
        
        document.getElementById('startDate').value = todayStr;
        document.getElementById('endDate').value = todayStr;
    }

    // 직접설정 패널 숨김
    hideCustomPanel() {
        const panel = document.getElementById('customPeriodPanel');
        panel.classList.remove('active');
    }

    // 직접설정 적용
    applyCustomPeriod() {
        const startDateInput = document.getElementById('startDate');
        const endDateInput = document.getElementById('endDate');
        
        const startDate = new Date(startDateInput.value);
        const endDate = new Date(endDateInput.value);

        if (!startDateInput.value || !endDateInput.value) {
            alert('시작일과 종료일을 모두 선택해주세요.');
            return;
        }

        if (startDate > endDate) {
            alert('시작일은 종료일보다 빨라야 합니다.');
            return;
        }

        this.customStartDate = startDate;
        this.customEndDate = endDate;
        this.hideCustomPanel();
        this.updateSelectedPeriod('custom');
    }

    // 직접설정 취소
    cancelCustomPeriod() {
        this.hideCustomPanel();
        
        // 이전 기간으로 되돌리기
        if (this.currentPeriod === 'custom') {
            this.selectPeriod('today');
        }
    }

    // 날짜 입력 유효성 검사
    validateDateInputs() {
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        const applyBtn = document.getElementById('applyCustomPeriod');

        if (startDate && endDate) {
            const start = new Date(startDate);
            const end = new Date(endDate);
            
            if (start <= end) {
                applyBtn.disabled = false;
            } else {
                applyBtn.disabled = true;
            }
        } else {
            applyBtn.disabled = true;
        }
    }

    // 선택된 기간 업데이트
    updateSelectedPeriod(period) {
        const periodText = document.getElementById('periodText');
        const dateRange = document.getElementById('dateRange');
        const today = new Date();
        
        let startDate, endDate, text;

        switch (period) {
            case 'today':
                startDate = endDate = today;
                text = '오늘';
                break;
            case 'week':
                endDate = today;
                startDate = new Date(today);
                startDate.setDate(today.getDate() - 6);
                text = '1주일';
                break;
            case 'month':
                endDate = today;
                startDate = new Date(today);
                startDate.setMonth(today.getMonth() - 1);
                text = '1개월';
                break;
            case 'quarter':
                endDate = today;
                startDate = new Date(today);
                startDate.setMonth(today.getMonth() - 3);
                text = '3개월';
                break;
            case 'half-year':
                endDate = today;
                startDate = new Date(today);
                startDate.setMonth(today.getMonth() - 6);
                text = '6개월';
                break;
            case 'nine-months':
                endDate = today;
                startDate = new Date(today);
                startDate.setMonth(today.getMonth() - 9);
                text = '9개월';
                break;
            case 'year':
                endDate = today;
                startDate = new Date(today);
                startDate.setFullYear(today.getFullYear() - 1);
                text = '1년';
                break;
            case 'custom':
                if (this.customStartDate && this.customEndDate) {
                    startDate = this.customStartDate;
                    endDate = this.customEndDate;
                    text = '직접설정';
                } else {
                    return;
                }
                break;
            default:
                return;
        }

        // UI 업데이트
        periodText.textContent = text;
        
        if (startDate.getTime() === endDate.getTime()) {
            dateRange.textContent = this.formatDate(startDate);
        } else {
            dateRange.textContent = `${this.formatDate(startDate)} ~ ${this.formatDate(endDate)}`;
        }

        // 캘린더에 범위 표시
        if (window.calendar) {
            calendar.highlightDateRange(startDate, endDate);
        }

        // 커스텀 이벤트 발생
        window.dispatchEvent(new CustomEvent('periodSelected', {
            detail: {
                period: period,
                startDate: startDate,
                endDate: endDate,
                text: text
            }
        }));
    }

    // 날짜 포맷 (표시용)
    formatDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    // 날짜 포맷 (input용)
    formatDateForInput(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    // 기간 가져오기
    getCurrentPeriod() {
        return {
            period: this.currentPeriod,
            startDate: this.getStartDate(),
            endDate: this.getEndDate()
        };
    }

    // 시작일 가져오기
    getStartDate() {
        const today = new Date();
        
        switch (this.currentPeriod) {
            case 'today':
                return today;
            case 'week':
                const weekStart = new Date(today);
                weekStart.setDate(today.getDate() - 6);
                return weekStart;
            case 'month':
                const monthStart = new Date(today);
                monthStart.setMonth(today.getMonth() - 1);
                return monthStart;
            case 'quarter':
                const quarterStart = new Date(today);
                quarterStart.setMonth(today.getMonth() - 3);
                return quarterStart;
            case 'half-year':
                const halfYearStart = new Date(today);
                halfYearStart.setMonth(today.getMonth() - 6);
                return halfYearStart;
            case 'nine-months':
                const nineMonthsStart = new Date(today);
                nineMonthsStart.setMonth(today.getMonth() - 9);
                return nineMonthsStart;
            case 'year':
                const yearStart = new Date(today);
                yearStart.setFullYear(today.getFullYear() - 1);
                return yearStart;
            case 'custom':
                return this.customStartDate;
            default:
                return today;
        }
    }

    // 종료일 가져오기
    getEndDate() {
        const today = new Date();
        
        switch (this.currentPeriod) {
            case 'custom':
                return this.customEndDate;
            default:
                return today;
        }
    }
}

// 전역 기간 선택자 인스턴스
let periodSelector;