# JPype Java 17+ 경고 해결 방법

## 문제 상황
KoNLPy를 사용할 때 다음과 같은 경고 메시지가 나타납니다:
```
WARNING: A restricted method in java.lang.System has been called
WARNING: java.lang.System::load has been called by org.jpype.JPypeContext
WARNING: Use --enable-native-access=ALL-UNNAMED to avoid a warning
```

## 해결 방법

### 방법 1: 실행 스크립트 사용 (권장)
Windows:
```bash
./run_app.bat
```

Linux/Mac:
```bash
./run_app.sh
```

### 방법 2: 환경 변수 직접 설정
Windows (PowerShell):
```powershell
$env:JAVA_TOOL_OPTIONS="--enable-native-access=ALL-UNNAMED --add-opens java.base/java.lang=ALL-UNNAMED"
python backend/app.py
```

Windows (CMD):
```cmd
set JAVA_TOOL_OPTIONS=--enable-native-access=ALL-UNNAMED --add-opens java.base/java.lang=ALL-UNNAMED
python backend/app.py
```

Linux/Mac:
```bash
export JAVA_TOOL_OPTIONS="--enable-native-access=ALL-UNNAMED --add-opens java.base/java.lang=ALL-UNNAMED"
python backend/app.py
```

### 방법 3: IDE 설정
VS Code, PyCharm 등에서 실행 시 환경 변수를 추가하세요:
- 변수명: `JAVA_TOOL_OPTIONS`
- 값: `--enable-native-access=ALL-UNNAMED --add-opens java.base/java.lang=ALL-UNNAMED`

## 설명
- 이 경고는 Java 17 이상에서 JPype가 Java의 제한된 시스템 메서드에 접근할 때 발생합니다.
- KoNLPy는 내부적으로 JPype를 사용하여 Java 기반 형태소 분석기와 통신합니다.
- 경고를 없애기 위해 Java에게 네이티브 액세스를 허용한다고 명시적으로 알려줍니다.
- 이는 보안 경고일 뿐 실제 동작에는 영향을 주지 않습니다.