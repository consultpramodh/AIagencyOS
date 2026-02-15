import json
from math import ceil
from urllib.parse import urlparse


PAID_PLATFORMS = [
    "Google Ads",
    "Meta Ads",
    "LinkedIn Ads",
    "Microsoft Ads",
    "YouTube Ads",
    "TikTok Ads",
    "X Ads",
    "Pinterest Ads",
    "Reddit Ads",
    "Snapchat Ads",
]

OBJECTIVES = ["Lead Generation", "Conversions", "Traffic", "Awareness", "Retargeting"]

PLATFORM_CONFIG = {
    "Google Ads": {
        "objectives": ["Lead Generation", "Conversions", "Traffic", "Awareness", "Retargeting"],
        "sub_options": {
            "Lead Generation": ["Search Leads", "Call Leads", "Local Services Leads", "Performance Max Leads"],
            "Conversions": ["Performance Max Sales", "Search Conversions", "Demand Gen Conversions"],
            "Traffic": ["Search Traffic", "Display Traffic", "Demand Gen Traffic"],
            "Awareness": ["Video Reach", "Display Reach", "Brand Lift"],
            "Retargeting": ["Display Remarketing", "YouTube Remarketing", "RLSA Search Retargeting"],
        },
        "templates": [
            "Local Lead Gen Search",
            "Brand Protection Search",
            "Competitor Conquest Search",
            "Performance Max Full-Funnel",
            "Display + YouTube Remarketing",
        ],
    },
    "YouTube Ads": {
        "objectives": ["Awareness", "Lead Generation", "Traffic", "Retargeting", "Conversions"],
        "sub_options": {
            "Awareness": ["Video Reach Campaign", "Non-Skippable Reach", "Bumper Reach", "Ad Sequence Storytelling"],
            "Lead Generation": ["Video Action Leads", "Demand Gen Leads", "Lead Form Extension"],
            "Traffic": ["Video Views", "In-Feed Traffic", "Demand Gen Clicks"],
            "Retargeting": ["Viewer Retargeting", "Site Visitor Retargeting", "Cart Abandon Retargeting"],
            "Conversions": ["Video Action Conversions", "Demand Gen Conversions"],
        },
        "templates": [
            "Views Accelerator",
            "Video Action Lead Gen",
            "Reach Burst + Bumper",
            "Sequential Story Campaign",
            "Demand Gen Conversion Push",
        ],
    },
    "Meta Ads": {
        "objectives": ["Awareness", "Traffic", "Lead Generation", "Conversions", "Retargeting"],
        "sub_options": {
            "Awareness": ["Reach", "Brand Awareness Video", "Advantage+ Awareness"],
            "Traffic": ["Landing Page Views", "Engagement Traffic", "Click to Message"],
            "Lead Generation": ["Instant Form Leads", "Website Leads", "Click to WhatsApp Leads"],
            "Conversions": ["Sales Conversions", "Catalog Sales", "Advantage+ Shopping"],
            "Retargeting": ["Website Visitors", "Engaged Audience", "Abandoned Checkout"],
        },
        "templates": [
            "Instant Form Lead Gen",
            "Click-to-WhatsApp Leads",
            "Advantage+ Shopping",
            "Creative Testing Sprint",
            "Dynamic Retargeting Carousel",
        ],
    },
    "LinkedIn Ads": {
        "objectives": ["Lead Generation", "Awareness", "Traffic", "Conversions", "Retargeting"],
        "sub_options": {
            "Lead Generation": ["Lead Gen Forms", "Conversation Ads Lead Capture", "Event Registration Leads"],
            "Awareness": ["Brand Awareness Sponsored Content", "Video Thought Leadership"],
            "Traffic": ["Website Visits", "Document Ad Traffic", "Follower Growth"],
            "Conversions": ["Website Conversions", "Demo Request Conversions"],
            "Retargeting": ["Matched Audiences", "Website Retargeting", "Account-Based Retargeting"],
        },
        "templates": [
            "B2B Lead Gen Form",
            "Thought Leadership + Retarget",
            "ABM Target Account Push",
            "Webinar Registration Funnel",
        ],
    },
    "Microsoft Ads": {
        "objectives": ["Lead Generation", "Conversions", "Traffic", "Retargeting", "Awareness"],
        "sub_options": {
            "Lead Generation": ["Search Lead Capture", "Call Extensions Leads", "Local Service Leads"],
            "Conversions": ["Search Conversions", "Performance Max Conversions", "Shopping Conversions"],
            "Traffic": ["Search Traffic", "Audience Traffic"],
            "Retargeting": ["Audience Remarketing", "Dynamic Remarketing"],
            "Awareness": ["Audience Ads Awareness", "Native Reach"],
        },
        "templates": [
            "Google Import + Improve",
            "Bing Search Lead Gen",
            "Microsoft Audience Retargeting",
            "Shopping + Search Hybrid",
        ],
    },
    "TikTok Ads": {
        "objectives": ["Awareness", "Traffic", "Lead Generation", "Conversions", "Retargeting"],
        "sub_options": {
            "Awareness": ["Reach", "Video Views", "Brand Lift"],
            "Traffic": ["Landing Page Traffic", "Profile Visits", "App Traffic"],
            "Lead Generation": ["Instant Form Leads", "Website Leads", "Message Leads"],
            "Conversions": ["Website Conversions", "Catalog Sales", "App Conversions"],
            "Retargeting": ["Viewer Retargeting", "Site Retargeting", "Cart Retargeting"],
        },
        "templates": [
            "UGC Awareness Burst",
            "TikTok Lead Form Sprint",
            "Spark Ads Conversion Push",
            "Creator Whitelist Retargeting",
        ],
    },
    "X Ads": {
        "objectives": ["Awareness", "Traffic", "Lead Generation", "Conversions"],
        "sub_options": {
            "Awareness": ["Reach Campaign", "Video Views"],
            "Traffic": ["Website Traffic", "App Clicks"],
            "Lead Generation": ["Website Lead Capture", "DM Lead Capture"],
            "Conversions": ["Website Conversions", "App Conversions"],
        },
        "templates": [
            "Real-Time Event Traffic",
            "Website Click Funnel",
            "Video Views + Retarget",
        ],
    },
    "Pinterest Ads": {
        "objectives": ["Awareness", "Traffic", "Conversions"],
        "sub_options": {
            "Awareness": ["Brand Awareness", "Video Awareness"],
            "Traffic": ["Consideration Traffic", "Search Traffic"],
            "Conversions": ["Catalog Sales", "Checkout Conversions", "Lead Conversions"],
        },
        "templates": [
            "Evergreen Pin Traffic",
            "Shopping Catalog Conversions",
            "Seasonal Planning Campaign",
        ],
    },
    "Reddit Ads": {
        "objectives": ["Awareness", "Traffic", "Conversions"],
        "sub_options": {
            "Awareness": ["Conversation Reach", "Community Awareness"],
            "Traffic": ["Website Traffic", "Landing Page Clicks"],
            "Conversions": ["Website Conversions", "Lead Submit Conversions"],
        },
        "templates": [
            "Subreddit Interest Awareness",
            "High-Intent Traffic Threads",
            "Conversion Retargeting Wave",
        ],
    },
    "Snapchat Ads": {
        "objectives": ["Awareness", "Traffic", "Lead Generation", "Conversions"],
        "sub_options": {
            "Awareness": ["Reach", "Story Views", "AR Lens Awareness"],
            "Traffic": ["Website Traffic", "App Traffic"],
            "Lead Generation": ["Instant Form Leads", "Message Leads"],
            "Conversions": ["Website Conversions", "App Installs", "Catalog Sales"],
        },
        "templates": [
            "Story Reach Blast",
            "Lead Form Collection",
            "App Install Growth",
            "Snap Retargeting Recovery",
        ],
    },
}

PLATFORM_OBJECTIVES = {platform: config["objectives"] for platform, config in PLATFORM_CONFIG.items()}


def _keyword_seed_from_client(client_name: str) -> list[str]:
    words = [w.strip().lower() for w in client_name.replace("-", " ").split() if len(w.strip()) >= 3]
    return list(dict.fromkeys(words))[:5]


def keyword_suggestions(client_name: str, objective: str, existing: list[str] | None = None) -> list[str]:
    existing = existing or []
    base = _keyword_seed_from_client(client_name or "local business")
    objective_terms = {
        "lead generation": ["near me", "quote", "best", "services", "book now"],
        "conversions": ["buy", "pricing", "offer", "discount", "trusted"],
        "traffic": ["guide", "tips", "ideas", "how to", "examples"],
        "awareness": ["brand", "top", "why choose", "local", "expert"],
        "retargeting": ["return", "finish order", "book today", "limited slots", "follow up"],
    }
    terms = objective_terms.get(objective.lower(), ["near me", "services", "book now"])
    combos = []
    for b in base or ["local business"]:
        for t in terms:
            combos.append(f"{b} {t}".strip())
    all_keywords = [*existing, *combos, *[f"{b} agency" for b in base]]
    dedup = list(dict.fromkeys([k.strip() for k in all_keywords if k.strip()]))
    return dedup[:20]


def campaign_plan(
    platform: str,
    objective: str,
    budget_cents: int,
    days: int,
    client_name: str,
    existing_keywords: list[str] | None = None,
    sub_option: str | None = None,
    template_name: str | None = None,
) -> dict:
    safe_days = max(1, days)
    daily_budget_cents = ceil(max(0, budget_cents) / safe_days)

    bid_by_objective = {
        "lead generation": "Maximize Conversions (with TCPA after 20-30 conversions)",
        "conversions": "Maximize Conversion Value",
        "traffic": "Maximize Clicks with CPC cap",
        "awareness": "Target Impression Share / Reach",
        "retargeting": "Maximize Conversions (Audience-only)",
    }
    objective_key = objective.lower()
    bid_strategy = bid_by_objective.get(objective_key, "Maximize Conversions")

    platform_profiles = {
        "Google Ads": {
            "campaign_type": "Search",
            "recommended_networks": "Search + Retargeting",
            "audience_setup": "Intent keywords + remarketing list",
            "conversion_event": "Qualified lead form submit",
            "attribution_window": "30-day click",
            "placement_control": "Search partners OFF initially; Display OFF for lead-gen launch",
        },
        "Microsoft Ads": {
            "campaign_type": "Search",
            "recommended_networks": "Search + Audience retargeting",
            "audience_setup": "Intent keywords + LinkedIn profile targeting",
            "conversion_event": "Lead form submit / call",
            "attribution_window": "30-day click",
            "placement_control": "Audience network limited at launch",
        },
        "Meta Ads": {
            "campaign_type": "Leads / Sales",
            "recommended_networks": "Feeds + Stories + Reels",
            "audience_setup": "Interest stack + lookalike + engaged retargeting",
            "conversion_event": "Lead form submit / landing page conversion",
            "attribution_window": "7-day click / 1-day view",
            "placement_control": "Advantage+ placements with exclusions after week 1",
        },
        "LinkedIn Ads": {
            "campaign_type": "Lead Gen Forms",
            "recommended_networks": "Sponsored Content + Lead Gen Forms",
            "audience_setup": "Job title + industry + company size filters",
            "conversion_event": "Qualified lead form submit",
            "attribution_window": "30-day click / 7-day view",
            "placement_control": "Audience expansion OFF initially",
        },
        "YouTube Ads": {
            "campaign_type": "Video Action / Demand Gen",
            "recommended_networks": "YouTube In-Stream + In-Feed",
            "audience_setup": "Custom intent + remarketing audiences",
            "conversion_event": "Site lead / engaged view",
            "attribution_window": "30-day click / engaged-view",
            "placement_control": "Exclude kids content + low-quality placements",
        },
        "TikTok Ads": {
            "campaign_type": "Traffic / Conversions",
            "recommended_networks": "TikTok Feed",
            "audience_setup": "Interest + behavior + website retargeting",
            "conversion_event": "Lead submit / key page view",
            "attribution_window": "7-day click / 1-day view",
            "placement_control": "Automated creative ON, tighten after 3 days",
        },
        "X Ads": {
            "campaign_type": "Website Traffic / Leads",
            "recommended_networks": "Timeline placements",
            "audience_setup": "Keyword + follower lookalike targeting",
            "conversion_event": "Landing page lead",
            "attribution_window": "30-day click",
            "placement_control": "Brand safety exclusions enabled",
        },
        "Pinterest Ads": {
            "campaign_type": "Consideration / Conversions",
            "recommended_networks": "Home feed + search placements",
            "audience_setup": "Interest + keyword + actalike",
            "conversion_event": "Signup / checkout",
            "attribution_window": "30-day click / 7-day view",
            "placement_control": "Catalog + shopping disabled if no product feed",
        },
        "Reddit Ads": {
            "campaign_type": "Traffic / Conversions",
            "recommended_networks": "Feed placements",
            "audience_setup": "Subreddit targeting + interest groups",
            "conversion_event": "Lead submit / key action",
            "attribution_window": "28-day click / 1-day view",
            "placement_control": "Brand safety filter high",
        },
        "Snapchat Ads": {
            "campaign_type": "Lead Gen / Conversions",
            "recommended_networks": "Story + Spotlight placements",
            "audience_setup": "Lifestyle + custom audience retargeting",
            "conversion_event": "Lead submit",
            "attribution_window": "7-day click / 1-day view",
            "placement_control": "Auto-bid initially, cap after baseline CPA",
        },
    }
    profile = platform_profiles.get(
        platform,
        {
            "campaign_type": "Performance",
            "recommended_networks": "Core placement + remarketing",
            "audience_setup": "Local radius + in-market audiences",
            "conversion_event": "Primary lead event",
            "attribution_window": "30-day click",
            "placement_control": "Start broad, then tighten by performance",
        },
    )
    platform_config = PLATFORM_CONFIG.get(platform, {})
    sub_options = platform_config.get("sub_options", {}).get(objective, [])
    selected_sub_option = sub_option if sub_option in sub_options else (sub_options[0] if sub_options else "Standard")
    template_library = platform_config.get("templates", [])
    selected_template = template_name if template_name in template_library else (template_library[0] if template_library else "Standard Template")

    keyword_list = keyword_suggestions(client_name, objective, existing_keywords)

    return {
        "platform": platform,
        "objective": objective,
        "sub_option": selected_sub_option,
        "available_sub_options": sub_options,
        "template_name": selected_template,
        "total_budget_cents": budget_cents,
        "days": safe_days,
        "daily_budget_cents": daily_budget_cents,
        "bid_strategy": bid_strategy,
        "recommended_networks": profile["recommended_networks"],
        "campaign_type": profile["campaign_type"],
        "audience_setup": profile["audience_setup"],
        "conversion_event": profile["conversion_event"],
        "attribution_window": profile["attribution_window"],
        "placement_control": profile["placement_control"],
        "ad_set_count": 2 if safe_days <= 7 else 3,
        "top_templates": template_library,
        "keywords_suggested": keyword_list,
        "efficiency_checklist": [
            "Enable conversion tracking before launch",
            "Use at least 2 ad variants per ad set",
            "Start with exact/phrase match for high-intent terms",
            "Add negative keywords from day 1",
            "Review search terms and placements every 48 hours",
            "Pause underperforming ads after 300+ impressions",
        ],
        "definitions": {
            "daily_budget": "total_budget / days",
            "keyword_source": "client name + objective heuristics + existing campaign keywords",
            "update_rule": "recompute on campaign save or when budget/days/objective changes",
        },
    }


def parse_keywords(raw_keywords: str) -> list[str]:
    parts = [x.strip() for x in (raw_keywords or "").replace("\n", ",").split(",")]
    return [x for x in parts if x]


def parse_handles(raw_handles: str) -> list[str]:
    parts = [x.strip().lstrip("@") for x in (raw_handles or "").replace("\n", ",").split(",")]
    return [x for x in parts if x]


def normalize_website_url(raw_value: str) -> str:
    value = (raw_value or "").strip()
    if not value:
        return ""
    if value.startswith(("http://", "https://")):
        return value
    return f"https://{value}"


def _website_slug(website_url: str) -> str:
    parsed = urlparse((website_url or "").strip())
    host = parsed.netloc or parsed.path
    host = host.replace("www.", "").strip("/")
    if not host:
        return "your-brand"
    return host.split(".")[0].replace("-", " ")


def seo_content_pack(client_name: str, website_url: str, social_handles: list[str], objective: str, keywords: list[str]) -> dict:
    primary_kw = keywords[0] if keywords else f"{client_name.lower()} services"
    support_kw = keywords[1:5] if len(keywords) > 1 else [f"{client_name.lower()} near me", "local service provider"]
    website_topic = _website_slug(website_url)

    title = f"{client_name}: {objective} playbook for {website_topic}"
    meta_description = (
        f"Learn how {client_name} can improve {objective.lower()} with a focused campaign strategy, "
        f"high-intent keywords, and conversion-ready landing pages."
    )[:158]

    social_refs = [f"@{h}" for h in social_handles[:3]]
    social_line = ", ".join(social_refs) if social_refs else "your social channels"

    return {
        "source": {
            "website_url": website_url or "—",
            "social_handles": social_handles,
        },
        "seo_targets": {
            "primary_keyword": primary_kw,
            "supporting_keywords": support_kw,
            "search_intent": "commercial + local intent",
        },
        "on_page": {
            "title_tag": title,
            "meta_description": meta_description,
            "h1": f"{client_name} {objective} Strategy",
            "suggested_slugs": [
                f"/{primary_kw.replace(' ', '-')}",
                f"/{client_name.lower().replace(' ', '-')}-services",
            ],
        },
        "content_draft": {
            "blog_title": f"How {client_name} can win more {objective.lower()} this quarter",
            "outline": [
                "Current market demand and customer intent",
                "Keyword clusters and landing page map",
                "Channel mix and budget allocation",
                "Conversion tracking and optimization cadence",
                "90-day measurement plan",
            ],
            "cta": f"Book a strategy call with {client_name} today.",
        },
        "social_content": {
            "channels": social_refs,
            "posts": [
                f"We're optimizing {primary_kw} campaigns for better lead quality. Follow {social_line} for weekly results.",
                f"New campaign sprint: stronger landing pages + smarter keyword groups = better ROI. #{objective.replace(' ', '')}",
                f"Behind the scenes: conversion tracking upgrades now live for {client_name}.",
            ],
        },
        "technical_seo_checklist": [
            "Ensure one primary H1 per landing page",
            "Add internal links from top-traffic pages",
            "Compress hero media and improve Core Web Vitals",
            "Connect Search Console and validate indexing",
            "Track form submits and call clicks as conversions",
        ],
    }


def campaign_plan_json(platform: str, objective: str, budget_cents: int, days: int, client_name: str, existing_keywords: list[str] | None = None) -> str:
    return json.dumps(campaign_plan(platform, objective, budget_cents, days, client_name, existing_keywords), ensure_ascii=True)
