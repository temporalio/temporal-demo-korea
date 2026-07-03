# Workflow Diagrams / 워크플로우 다이어그램

## FortuneWorkflow (One-shot Fortune Reading / 일회성 운세)

### English

```mermaid
flowchart TD
    A([Start Workflow]) --> B[/"Input: name, birth_date, MBTI, language"/]
    B --> C["Activity: calculate_saju<br/>(Four Pillars calculation)"]
    C --> D["Activity: analyze_mbti<br/>(MBTI personality analysis)"]
    D --> E["Activity: generate_fortune<br/>(LLM call via OpenAI GPT-5.5)"]
    E --> F{LLM call<br/>succeeded?}
    F -- Yes --> G([Return FortuneReading])
    F -- "No (retry up to 3x)" --> E

    style A fill:#4F46E5,color:#fff
    style G fill:#16A34A,color:#fff
    style E fill:#F59E0B,color:#000
    style F fill:#EF4444,color:#fff
```

### 한국어

```mermaid
flowchart TD
    A([워크플로우 시작]) --> B[/"입력: 이름, 생년월일, MBTI, 언어"/]
    B --> C["액티비티: 사주 계산<br/>(천간/지지 기반 사주팔자)"]
    C --> D["액티비티: MBTI 분석<br/>(성격 유형 분석)"]
    D --> E["액티비티: 운세 생성<br/>(OpenAI GPT-5.5 LLM 호출)"]
    E --> F{LLM 호출<br/>성공?}
    F -- 성공 --> G([운세 결과 반환])
    F -- "실패 (최대 3회 재시도)" --> E

    style A fill:#4F46E5,color:#fff
    style G fill:#16A34A,color:#fff
    style E fill:#F59E0B,color:#000
    style F fill:#EF4444,color:#fff
```

---

## InteractiveFortuneWorkflow (Interactive Booth / 대화형 운세 부스)

### English

```mermaid
flowchart TD
    A([Start Workflow<br/>- runs forever -]) --> W{Wait for<br/>user input}

    W --> L["Update: language<br/>(ko / en)"]
    L --> N["Update: name"]
    N --> BD["Update: birth_date<br/>(YYYY-MM-DD)"]
    BD --> BT["Update: birth_time<br/>(optional)"]
    BT --> G["Update: gender<br/>(optional)"]
    G --> M["Update: mbti<br/>(optional)"]

    M --> S1["Activity: calculate_saju"]
    S1 --> S2["Activity: analyze_mbti"]
    S2 --> S3["Activity: generate_fortune<br/>(LLM, retry x3)"]
    S3 --> R([Return FortuneReading<br/>via Update response])

    R --> W

    L -. "exit" .-> X([Workflow completes])
    N -. "exit" .-> X
    BD -. "exit" .-> X
    BT -. "exit" .-> X
    G -. "exit" .-> X
    M -. "exit" .-> X

    style A fill:#4F46E5,color:#fff
    style R fill:#16A34A,color:#fff
    style X fill:#EF4444,color:#fff
    style W fill:#6366F1,color:#fff
    style S3 fill:#F59E0B,color:#000
```

### 한국어

```mermaid
flowchart TD
    A([워크플로우 시작<br/>- 무한 루프 -]) --> W{사용자 입력<br/>대기}

    W --> L["업데이트: 언어 선택<br/>(ko / en)"]
    L --> N["업데이트: 이름"]
    N --> BD["업데이트: 생년월일<br/>(YYYY-MM-DD)"]
    BD --> BT["업데이트: 태어난 시간<br/>(선택)"]
    BT --> G["업데이트: 성별<br/>(선택)"]
    G --> M["업데이트: MBTI<br/>(선택)"]

    M --> S1["액티비티: 사주 계산"]
    S1 --> S2["액티비티: MBTI 분석"]
    S2 --> S3["액티비티: 운세 생성<br/>(LLM, 재시도 3회)"]
    S3 --> R([운세 결과 반환<br/>업데이트 응답으로])

    R --> W

    L -. "exit 입력" .-> X([워크플로우 종료])
    N -. "exit 입력" .-> X
    BD -. "exit 입력" .-> X
    BT -. "exit 입력" .-> X
    G -. "exit 입력" .-> X
    M -. "exit 입력" .-> X

    style A fill:#4F46E5,color:#fff
    style R fill:#16A34A,color:#fff
    style X fill:#EF4444,color:#fff
    style W fill:#6366F1,color:#fff
    style S3 fill:#F59E0B,color:#000
```

---

## Temporal Features Highlighted / 활용된 Temporal 기능

| Feature | FortuneWorkflow | InteractiveFortuneWorkflow |
|---|---|---|
| `@workflow.run` | One-shot execution | Infinite loop |
| `@workflow.update` | - | Step-by-step input (request-response) |
| `@workflow.query` | `status`, `result` | `current_prompt`, `session_number` |
| `@workflow.signal` | - | `shutdown` |
| `RetryPolicy` | LLM activity (3x) | LLM activity (3x) |
| `workflow.upsert_memo` | - | Records each step's input |
| Durable execution | Survives worker restart | Survives disconnect + reconnect |
