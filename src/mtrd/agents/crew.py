from __future__ import annotations

import argparse
import os

from crewai import Agent, Task, Crew
from langchain_community.chat_models import ChatOllama


def build_crew(topic: str, audience: str):
    llm = ChatOllama(model=os.getenv("OLLAMA_MODEL", "phi3:latest"))

    researcher = Agent(
        role="Researcher",
        goal=f"Gather key signals about {topic} for {audience}",
        backstory="You find credible sources and summarize signals.",
        llm=llm,
    )

    analyst = Agent(
        role="Analyst",
        goal="Synthesize signals into risks and opportunities",
        backstory="You prioritize evidence and highlight conflicts.",
        llm=llm,
    )

    editor = Agent(
        role="Editor",
        goal="Produce a concise, decision-ready brief",
        backstory="You organize insights into a structured summary.",
        llm=llm,
    )

    t1 = Task(description=f"Collect signals and evidence about {topic}.", agent=researcher)
    t2 = Task(description="Analyze risks and opportunities from signals.", agent=analyst)
    t3 = Task(description="Write a concise brief for executives.", agent=editor)

    return Crew(agents=[researcher, analyst, editor], tasks=[t1, t2, t3])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument("--audience", required=True)
    args = parser.parse_args()

    crew = build_crew(args.topic, args.audience)
    result = crew.kickoff()
    print(result)


if __name__ == "__main__":
    main()
