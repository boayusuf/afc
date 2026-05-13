# AFC × Community Notes

Artefact for the dissertation *Benchmarking Automated Fact-Checking Pipelines Against X Community Notes* (Yusuf Shakir, 33114323, UWL, 2026).

This app runs a user-supplied claim through five Automated Fact-Checking (AFC) systems in parallel and displays their verdicts side-by-side. It is the live counterpart to the offline 5,469-claim benchmark reported in the dissertation.

## Systems

| ID | Paradigm | Backend |
|----|----------|---------|
| A  | Parametric LLM (closed-source) | GPT-4o via OpenAI |
| B  | Naive RAG | GPT-4o + Tavily search |
| C  | Professional fact-check API | Google Fact Check Tools |
| D  | Credibility-filtered RAG | GPT-4o + filtered Tavily |
| E  | Parametric LLM (open-source) | Llama 3.3 70B via Groq |

Each system returns a verdict (`TRUE`, `MISLEADING`, `MIXED`, or `NO_RESULT`), a short reasoning, and latency.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your four API keys
streamlit run app.py
```

The app launches at `http://localhost:8501`.

## API keys required

- `OPENAI_API_KEY` — https://platform.openai.com/api-keys
- `GROQ_API_KEY` — https://console.groq.com/keys
- `TAVILY_API_KEY` — https://app.tavily.com/home
- `GOOGLE_FACT_CHECK_API_KEY` — https://console.cloud.google.com/apis/credentials (enable Fact Check Tools API)

Missing a key? The corresponding system shows as unavailable; the others still run.

## Rate limit

The app caps each browser session at 20 claim runs to prevent runaway API costs. Refresh the page to reset.
