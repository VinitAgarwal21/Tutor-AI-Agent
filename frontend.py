from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Iterator, Tuple

import pandas as pd
import streamlit as st

# Import compiled LangGraph app
from backend import app


# -----------------------------
# Helpers
# -----------------------------
def safe_slug(title: str) -> str:
    s = title.strip().lower()
    s = re.sub(r"[^a-z0-9 _-]+", "", s)
    s = re.sub(r"\s+", "_", s).strip("_")
    return s or "blog"


def try_stream(graph_app, inputs: Dict[str, Any]) -> Iterator[Tuple[str, Any]]:
    """
    Stream graph progress if available; else invoke.
    """
    try:
        for step in graph_app.stream(inputs, stream_mode="updates"):
            yield ("updates", step)

        out = graph_app.invoke(inputs)
        yield ("final", out)
        return

    except Exception:
        pass

    try:
        for step in graph_app.stream(inputs, stream_mode="values"):
            yield ("values", step)

        out = graph_app.invoke(inputs)
        yield ("final", out)
        return

    except Exception:
        pass

    out = graph_app.invoke(inputs)
    yield ("final", out)


def extract_latest_state(current_state: Dict[str, Any], step_payload: Any) -> Dict[str, Any]:
    if isinstance(step_payload, dict):

        if (
            len(step_payload) == 1
            and isinstance(next(iter(step_payload.values())), dict)
        ):
            inner = next(iter(step_payload.values()))
            current_state.update(inner)

        else:
            current_state.update(step_payload)

    return current_state


# -----------------------------
# Past blogs helpers
# -----------------------------
def list_past_blogs() -> List[Path]:
    cwd = Path(".")
    files = [p for p in cwd.glob("*.md") if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files


def read_md_file(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def extract_title_from_md(md: str, fallback: str) -> str:
    for line in md.splitlines():
        if line.startswith("# "):
            t = line[2:].strip()
            return t or fallback

    return fallback


# -----------------------------
# Streamlit Config
# -----------------------------
st.set_page_config(
    page_title="AI Notes Generation Agent",
    layout="wide",
)

st.title("AI Notes Generation Agent")


# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:

    st.header("Generate Notes")

    topic = st.text_area(
        "Topic",
        height=120,
        placeholder="Enter a topic...",
    )

    as_of = st.date_input(
        "As-of date",
        value=date.today(),
    )

    run_btn = st.button(
        "Generate Notes",
        type="primary",
    )

    st.divider()

    st.subheader("Past Notes")

    past_files = list_past_blogs()

    if not past_files:
        st.caption("No saved notes found.")

    else:
        options = []
        file_by_label = {}

        for p in past_files[:50]:

            try:
                md_text = read_md_file(p)
                title = extract_title_from_md(md_text, p.stem)

            except Exception:
                title = p.stem

            label = f"{title} · {p.name}"

            options.append(label)
            file_by_label[label] = p

        selected_label = st.radio(
            "Select Notes",
            options=options,
            label_visibility="collapsed",
        )

        selected_md_file = file_by_label.get(selected_label)

        if st.button("Load Notes"):

            if selected_md_file:

                md_text = read_md_file(selected_md_file)

                st.session_state["last_out"] = {
                    "plan": None,
                    "final": md_text,
                }


# -----------------------------
# Session State
# -----------------------------
if "last_out" not in st.session_state:
    st.session_state["last_out"] = None


# -----------------------------
# Tabs
# -----------------------------
tab_plan, tab_preview = st.tabs(
    [
        "Logs",
        "Notes Preview",
    ]
)


# -----------------------------
# Run Blog Generation
# -----------------------------
if run_btn:

    if not topic.strip():
        st.warning("Please enter a topic.")
        st.stop()

    inputs: Dict[str, Any] = {
        "topic": topic.strip(),
        "mode": "",
        "needs_research": False,
        "queries": [],
        "evidence": [],
        "plan": None,
        "as_of": as_of.isoformat(),
        "recency_days": 7,
        "sections": [],
        "merged_md": "",
        "md_with_placeholders": "",
        "image_specs": [],
        "final": "",
    }

    status = st.status(
        "Running blog generation...",
        expanded=True,
    )

    progress_area = st.empty()

    current_state: Dict[str, Any] = {}

    last_node = None

    for kind, payload in try_stream(app, inputs):

        if kind in ("updates", "values"):

            node_name = None

            if (
                isinstance(payload, dict)
                and len(payload) == 1
                and isinstance(next(iter(payload.values())), dict)
            ):
                node_name = next(iter(payload.keys()))

            if node_name and node_name != last_node:
                status.write(f"➡️ Node: `{node_name}`")
                last_node = node_name

            current_state = extract_latest_state(
                current_state,
                payload,
            )

            summary = {
                "mode": current_state.get("mode"),
                "needs_research": current_state.get("needs_research"),
                "queries": (
                    current_state.get("queries", [])[:5]
                    if isinstance(current_state.get("queries"), list)
                    else []
                ),
                "evidence_count": len(
                    current_state.get("evidence", []) or []
                ),
                "tasks": len(
                    (
                        current_state.get("plan") or {}
                    ).get("tasks", [])
                )
                if isinstance(current_state.get("plan"), dict)
                else None,
                "sections_done": len(
                    current_state.get("sections", []) or []
                ),
            }

            progress_area.json(summary)

        elif kind == "final":

            out = payload

            st.session_state["last_out"] = out

            status.update(
                label="✅ Blog Generated",
                state="complete",
                expanded=False,
            )


# -----------------------------
# Render Output
# -----------------------------
out = st.session_state.get("last_out")

if out:

    # -----------------------------
    # Plan Tab
    # -----------------------------
    with tab_plan:

        st.subheader("Blog Plan")

        plan_obj = out.get("plan")

        if not plan_obj:
            st.info("No plan available.")

        else:

            if hasattr(plan_obj, "model_dump"):
                plan_dict = plan_obj.model_dump()

            elif isinstance(plan_obj, dict):
                plan_dict = plan_obj

            else:
                plan_dict = json.loads(
                    json.dumps(plan_obj, default=str)
                )

            st.write(
                "##",
                plan_dict.get("blog_title", "Untitled Blog"),
            )

            cols = st.columns(3)

            cols[0].write(
                f"**Audience:** {plan_dict.get('audience')}"
            )

            cols[1].write(
                f"**Tone:** {plan_dict.get('tone')}"
            )

            cols[2].write(
                f"**Type:** {plan_dict.get('blog_kind')}"
            )

            tasks = plan_dict.get("tasks", [])

            if tasks:

                df = pd.DataFrame(
                    [
                        {
                            "ID": t.get("id"),
                            "Title": t.get("title"),
                            "Words": t.get("target_words"),
                            "Research": t.get("requires_research"),
                            "Citations": t.get("requires_citations"),
                            "Code": t.get("requires_code"),
                            "Tags": ", ".join(t.get("tags") or []),
                        }
                        for t in tasks
                    ]
                ).sort_values("ID")

                st.dataframe(
                    df,
                    width="stretch",
                    hide_index=True,
                )

                with st.expander("Task Details"):
                    st.json(tasks)

    # -----------------------------
    # Markdown Preview Tab
    # -----------------------------
    with tab_preview:

        st.subheader("Markdown Preview")

        final_md = out.get("final") or ""

        if not final_md:
            st.warning("No markdown generated.")

        else:

            st.markdown(final_md)

            plan_obj = out.get("plan")

            if hasattr(plan_obj, "blog_title"):
                blog_title = plan_obj.blog_title

            elif isinstance(plan_obj, dict):
                blog_title = plan_obj.get(
                    "blog_title",
                    "blog",
                )

            else:
                blog_title = extract_title_from_md(
                    final_md,
                    "blog",
                )

            md_filename = f"{safe_slug(blog_title)}.md"

            st.download_button(
                "⬇️ Download Markdown",
                data=final_md.encode("utf-8"),
                file_name=md_filename,
                mime="text/markdown",
            )

else:
    st.info("Enter a topic and click 'Generate Blog'.")