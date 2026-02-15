import json

QUESTIONS = [
    "What business outcome do you want in 90 days?",
    "What is your budget and team capacity?",
    "Which channels matter most (SEO, Ads, Email, Social)?",
    "What inputs/data do you already have?",
    "Who must approve changes before launch?",
    "What risks could block delivery?",
    "What timeline or launch date matters most?",
]


def default_questions() -> list[str]:
    return QUESTIONS


def build_recommendation(title: str, answers: list[str]) -> dict:
    answer_text = " ".join(a.lower() for a in answers if a)
    channels = []
    for c in ["seo", "ads", "email", "social"]:
        if c in answer_text:
            channels.append(c)
    if not channels:
        channels = ["seo", "ads"]

    agents = {
        "head": {"agent_key": "strategy_lead", "name": "Strategy Lead"},
        "sub_agents": [
            {"agent_key": "content_ops", "responsibility": "Content and messaging"},
            {"agent_key": "paid_media", "responsibility": "Campaign setup and optimization"},
            {"agent_key": "reporting_ops", "responsibility": "Weekly reporting and insights"},
        ],
    }

    steps = [
        {"order": 1, "name": "Discovery brief", "action_type": "plan", "agent_key": "strategy_lead", "gating_policy": "approve"},
        {"order": 2, "name": "Asset prep", "action_type": "content", "agent_key": "content_ops", "gating_policy": "approve"},
        {"order": 3, "name": "Launch channel work", "action_type": "execute", "agent_key": "paid_media", "gating_policy": "approve"},
        {"order": 4, "name": "Weekly report", "action_type": "report", "agent_key": "reporting_ops", "gating_policy": "approve"},
    ]

    metrics = {
        "primary": ["qualified_leads", "cost_per_lead", "close_rate"],
        "cadence": "weekly",
        "channels": channels,
    }

    return {
        "title": title,
        "agent_org": agents,
        "workflow_steps": steps,
        "metrics": metrics,
        "summary": json.dumps({"channels": channels, "answers": len(answers)}),
    }
