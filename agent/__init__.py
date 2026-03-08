"""
StoryForge Agent Package

root_agent is exported lazily so that importing agent.tools.image_tool
(used by main.py) does NOT trigger the full ADK import chain at startup.

The ADK dev UI (adk web) accesses root_agent via:
    from agent import root_agent
which triggers __getattr__ and loads agent.py on demand.
"""


def __getattr__(name: str):
    if name == "root_agent":
        from agent.agent import root_agent
        return root_agent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
