// 캘린더 관리 클래스
class Calendar {
    constructor() {
        this.currentDate = new Date();
        this.selectedDates = [];
        this.displayedMonths = [];
        this.init();
    }

    init() {
        this.generateCalendar();
        this.bindEvents();
        this.generateLast12Months();
    }

    // 최근 12개월 생성
    generateLast12Months() {
        const today = new Date();
        this.displayedMonths = [];
        
        for (let i = 11; i >= 0; i--) {
            const date = new Date(today.getFullYear(), today.getMonth() - i, 1);
            this.displayedMonths.push(date);
        }
        
        // 현재 표시할 월을 가장 최근 월(현재 월)로 설정
        this.currentDate = this.displayedMonths[this.displayedMonths.length - 1];
        this.generateCalendar();
    }

    // 캘린더 생성
    generateCalendar() {
        const calendarGrid = document.getElementById('calendarGrid');
        const currentMonth = document.getElementById('currentMonth');
        
        // 월 표시 업데이트
        const monthNames = [
            '1월', '2월', '3월', '4월', '5월', '6월',
            '7월', '8월', '9월', '10월', '11월', '12월'
        ];
        
        currentMonth.textContent = `${this.currentDate.getFullYear()}년 ${monthNames[this.currentDate.getMonth()]}`;
        
        // 캘린더 그리드 초기화
        calendarGrid.innerHTML = '';
        
        // 요일 헤더 추가
        const dayHeaders = ['일', '월', '화', '수', '목', '금', '토'];
        dayHeaders.forEach(day => {
            const dayHeader = document.createElement('div');
            dayHeader.className = 'calendar-day-header';
            dayHeader.textContent = day;
            calendarGrid.appendChild(dayHeader);
        });
        
        // 월의 첫째 날과 마지막 날
        const firstDay = new Date(this.currentDate.getFullYear(), this.currentDate.getMonth(), 1);
        const lastDay = new Date(this.currentDate.getFullYear(), this.currentDate.getMonth() + 1, 0);
        const today = new Date();
        
        // 이전 월의 마지막 며칠
        const startDay = firstDay.getDay();
        const prevMonth = new Date(this.currentDate.getFullYear(), this.currentDate.getMonth() - 1, 0);
        
        for (let i = startDay - 1; i >= 0; i--) {
            const day = prevMonth.getDate() - i;
            const dayElement = this.createDayElement(day, true, new Date(prevMonth.getFullYear(), prevMonth.getMonth(), day));
            calendarGrid.appendChild(dayElement);
        }
        
        // 현재 월의 모든 날들
        for (let day = 1; day <= lastDay.getDate(); day++) {
            const currentDay = new Date(this.currentDate.getFullYear(), this.currentDate.getMonth(), day);
            const dayElement = this.createDayElement(day, false, currentDay);
            
            // 오늘 날짜 표시
            if (this.isSameDate(currentDay, today)) {
                dayElement.classList.add('today');
            }
            
            calendarGrid.appendChild(dayElement);
        }
        
        // 다음 월의 첫 며칠
        const remainingCells = 42 - (startDay + lastDay.getDate()); // 6주 * 7일 = 42셀
        for (let day = 1; day <= remainingCells; day++) {
            const nextMonthDate = new Date(this.currentDate.getFullYear(), this.currentDate.getMonth() + 1, day);
            const dayElement = this.createDayElement(day, true, nextMonthDate);
            calendarGrid.appendChild(dayElement);
        }
    }

    // 날짜 엘리먼트 생성
    createDayElement(day, isOtherMonth, fullDate) {
        const dayElement = document.createElement('div');
        dayElement.className = 'calendar-day';
        dayElement.textContent = day;
        dayElement.dataset.date = fullDate.toISOString().split('T')[0];
        
        if (isOtherMonth) {
            dayElement.classList.add('other-month');
        }
        
        // 클릭 이벤트 추가
        dayElement.addEventListener('click', () => {
            this.selectDate(fullDate, dayElement);
        });
        
        return dayElement;
    }

    // 날짜 선택
    selectDate(date, element) {
        // 기존 선택 제거
        document.querySelectorAll('.calendar-day.selected').forEach(el => {
            el.classList.remove('selected');
        });
        
        // 새로운 선택 추가
        element.classList.add('selected');
        this.selectedDates = [date];
        
        // 커스텀 이벤트 발생
        window.dispatchEvent(new CustomEvent('dateSelected', { 
            detail: { date: date, formattedDate: this.formatDate(date) }
        }));
    }

    // 날짜 비교
    isSameDate(date1, date2) {
        return date1.getDate() === date2.getDate() &&
               date1.getMonth() === date2.getMonth() &&
               date1.getFullYear() === date2.getFullYear();
    }

    // 날짜 포맷
    formatDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    // 이벤트 바인딩
    bindEvents() {
        const prevBtn = document.getElementById('prevMonth');
        const nextBtn = document.getElementById('nextMonth');
        
        prevBtn.addEventListener('click', () => {
            this.previousMonth();
        });
        
        nextBtn.addEventListener('click', () => {
            this.nextMonth();
        });
    }

    // 이전 월
    previousMonth() {
        const currentIndex = this.displayedMonths.findIndex(month => 
            month.getMonth() === this.currentDate.getMonth() && 
            month.getFullYear() === this.currentDate.getFullYear()
        );
        
        if (currentIndex > 0) {
            this.currentDate = this.displayedMonths[currentIndex - 1];
            this.generateCalendar();
        }
    }

    // 다음 월
    nextMonth() {
        const currentIndex = this.displayedMonths.findIndex(month => 
            month.getMonth() === this.currentDate.getMonth() && 
            month.getFullYear() === this.currentDate.getFullYear()
        );
        
        if (currentIndex < this.displayedMonths.length - 1) {
            this.currentDate = this.displayedMonths[currentIndex + 1];
            this.generateCalendar();
        }
    }

    // 날짜 범위 표시
    highlightDateRange(startDate, endDate) {
        // 모든 날짜에서 범위 표시 제거
        document.querySelectorAll('.calendar-day').forEach(el => {
            el.classList.remove('in-range', 'selected');
        });

        if (!startDate || !endDate) return;

        // 날짜 범위 내의 모든 날짜 찾기
        const start = new Date(startDate);
        const end = new Date(endDate);
        
        document.querySelectorAll('.calendar-day').forEach(el => {
            const dateStr = el.dataset.date;
            if (dateStr) {
                const date = new Date(dateStr);
                if (date >= start && date <= end) {
                    if (this.isSameDate(date, start) || this.isSameDate(date, end)) {
                        el.classList.add('selected');
                    } else {
                        el.classList.add('in-range');
                    }
                }
            }
        });
    }

    // 현재 월로 이동
    goToCurrentMonth() {
        this.currentDate = new Date();
        this.generateCalendar();
    }
}

// 전역 캘린더 인스턴스
let calendar;