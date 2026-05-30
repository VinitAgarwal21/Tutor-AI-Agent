# AI Notes Generation Agent

A multi-agent pipeline that automatically researches, plans, and writes structured technical blog posts or study notes on any topic — with a Streamlit UI for real-time progress tracking and a Markdown preview/download.

---

## How It Works

The system is built as a **LangGraph state graph** with parallel section writing and an optional web research phase. Here's the high-level flow:

```
Topic Input
    │
    ▼
 [Router] ──► Decide: closed_book / hybrid / open_book
    │
    ├── needs_research=true ──► [Research] (Tavily web search)
    │                               │
    └── needs_research=false ───────┤
                                    ▼
                            [Orchestrator] ──► Generate blog plan (5–9 tasks)
                                    │
                              ┌─────┴─────┐
                              │  Fanout   │ (parallel workers)
                              └─────┬─────┘
                          [Worker × N] ──► Write each section
                                    │
                            [Reducer Subgraph]
                              merge_content
                                    │
                              decide_images
                                    │
                         generate_and_place_images
                                    │
                              Final Markdown
```

### Nodes

| Node | Role |
|---|---|
| **Router** | Classifies topic recency (`closed_book`, `hybrid`, `open_book`) and generates search queries if needed |
| **Research** | Runs Tavily queries, deduplicates results, filters by recency window |
| **Orchestrator** | Produces a structured `Plan` with typed tasks (title, goal, bullets, word count, flags) |
| **Worker** (parallel) | Writes one section per task; respects citations, code, and research flags |
| **Reducer → merge** | Sorts and joins all sections under the blog title |
| **Reducer → decide_images** | Plans up to 3 image placements with `[[IMAGE_N]]` placeholders |
| **Reducer → generate_and_place_images** | Fetches relevant images from Unsplash and inlines them; saves `.md` file |

---

## Project Structure

```
├── backend.py       # LangGraph graph definition (all nodes, schemas, subgraph)
├── frontend.py      # Streamlit UI (sidebar, tabs, streaming progress)
├── .env             # API keys (not committed)
└── *.md             # Saved output files (generated at runtime)
```

---

## Prerequisites

- Python 3.10+
- A [Google AI Studio](https://aistudio.google.com/) API key (Gemini)
- *(Optional)* A [Tavily](https://tavily.com/) API key for web research

---

## Installation

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd <repo-folder>

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

### `requirements.txt` (minimum)

```
langgraph
langchain-google-genai
langchain-core
langchain-community
pydantic
streamlit
pandas
python-dotenv
tavily-python          # optional, for web research
duckduckgo-search
requests
```

---

## Configuration

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your_google_ai_studio_key_here
TAVILY_API_KEY=your_tavily_api_key_here   # optional
```

If `TAVILY_API_KEY` is absent, research nodes return empty evidence and the agent falls back to closed-book mode.

---

## Running the App

```bash
streamlit run frontend.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Usage

1. **Enter a topic** in the sidebar text area (e.g. *"How does RAG work in LLMs"* or *"Latest developments in AI agents this week"*).
2. **Set the as-of date** (defaults to today) — used for recency filtering in research mode.
3. Click **Generate Notes**.
4. Watch live node progress in the **Logs** tab.
5. Read the rendered output in the **Notes Preview** tab.
6. Click **⬇️ Download Markdown** to save the file.
7. Previously generated notes are listed in the sidebar under **Past Notes** and can be reloaded.

---

## Research Modes

| Mode | When triggered | Recency window |
|---|---|---|
| `closed_book` | Evergreen concepts (e.g. "explain binary search") | None |
| `hybrid` | Mix of evergreen + recent tools/models | Last 45 days |
| `open_book` | News roundups, "latest", pricing, policy | Last 7 days |

In `open_book` mode, claims not backed by evidence URLs are flagged as *"Not found in provided sources."*

---

## Output

- A rendered Markdown preview in the browser.
- A `.md` file saved to the working directory (slug derived from the blog title).
- Up to 3 inline images sourced from Unsplash, placed where the LLM judges them most useful.

---


## Demo

https://github.com/VinitAgarwal21/Tutor-AI-Agent/blob/main/assets/Screenshot%201.png
<img width="1920" height="1080" alt="Screenshot (205)" src="https://github.com/user-attachments/assets/76ccd2b3-6939-485b-a4f5-a9a6b1286cc8" />



https://github.com/VinitAgarwal21/Tutor-AI-Agent/blob/main/assets/Screenshot%202.png
<img width="1920" height="1080" alt="Screenshot (206)" src="https://github.com/user-attachments/assets/434d572c-5de8-4e97-9bd8-289cca17ff75" />



https://github.com/VinitAgarwal21/Tutor-AI-Agent/blob/main/assets/Screenshot%203.png
<img width="1920" height="1080" alt="Screenshot (209)" src="https://github.com/user-attachments/assets/d13346cd-ba09-443b-80ec-7950e55889a8" />



https://github.com/VinitAgarwal21/Tutor-AI-Agent/blob/main/assets/Screenshot%204.png
<img width="1920" height="1080" alt="Screenshot (210)" src="https://github.com/user-attachments/assets/12acb972-b206-4002-b84b-e826d30c4131" />



https://github.com/VinitAgarwal21/Tutor-AI-Agent/blob/main/assets/Screenshot%205.png
 <img width="1920" height="1080" alt="Screenshot (211)" src="https://github.com/user-attachments/assets/3e4b100c-3f2c-4b80-86c0-1871cbc49322" />

https://github.com/VinitAgarwal21/Tutor-AI-Agent/blob/main/assets/AI%20Notes%20Generation%20Agent%20-%20Demo%20Video.mp4

## Notes & Limitations

- The LLM used is `gemini-3.1-flash-lite` (configurable in `backend.py`).
- Image fetching uses the Unsplash source API (no API key needed, but URLs may occasionally redirect or be unavailable).
- Parallel worker count equals the number of planned tasks (5–9), so generation time scales with task count and model latency.
- No authentication or multi-user isolation — intended for local/personal use.
