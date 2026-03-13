import json
from app.agents.common import client, settings

def get_hawkins_agent_level(hawkins_score: int) -> int:
    """Determine which level agent to use based on Hawkins score (1-10 system)."""
    if hawkins_score <= 20:   return 1
    if hawkins_score <= 50:   return 2
    if hawkins_score <= 100:  return 3
    if hawkins_score <= 175:  return 4
    if hawkins_score <= 200:  return 5
    if hawkins_score <= 310:  return 6
    if hawkins_score <= 400:  return 7
    if hawkins_score <= 500:  return 8
    if hawkins_score <= 600:  return 9
    return 10


