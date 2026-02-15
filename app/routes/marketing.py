import json

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import Client, MarketingCampaign, MarketingKeyword, Membership
from app.services.authz import CurrentContext, require_context, require_role
from app.services.intelligence import audit_change, emit_event
from app.services.marketing import (
    OBJECTIVES,
    PAID_PLATFORMS,
    PLATFORM_CONFIG,
    PLATFORM_OBJECTIVES,
    campaign_plan,
    keyword_suggestions,
    normalize_website_url,
    parse_handles,
    parse_keywords,
    seo_content_pack,
)

router = APIRouter(tags=["marketing"])
templates = Jinja2Templates(directory="app/templates")


def _base_context(ctx: CurrentContext, db: Session) -> dict:
    memberships = db.query(Membership).filter(Membership.user_id == ctx.user.id).all()
    clients = db.query(Client).filter(Client.tenant_id == ctx.tenant.id).order_by(Client.name.asc()).all()
    return {"ctx": ctx, "memberships": memberships, "clients": clients}


def _campaign_rows(ctx: CurrentContext, db: Session) -> list[dict]:
    rows = db.query(MarketingCampaign).filter(MarketingCampaign.tenant_id == ctx.tenant.id).order_by(MarketingCampaign.updated_at.desc()).all()
    clients = {c.id: c for c in db.query(Client).filter(Client.tenant_id == ctx.tenant.id).all()}
    keywords = db.query(MarketingKeyword).filter(MarketingKeyword.tenant_id == ctx.tenant.id).all()
    keywords_by_campaign: dict[int, list[str]] = {}
    for item in keywords:
        keywords_by_campaign.setdefault(item.campaign_id, []).append(item.keyword)

    output: list[dict] = []
    for row in rows:
        plan = {}
        try:
            plan = json.loads(row.plan_json or "{}")
        except json.JSONDecodeError:
            plan = {}
        output.append(
            {
                "id": row.id,
                "name": row.name,
                "platform": row.platform,
                "objective": row.objective,
                "client_name": clients[row.client_id].name if row.client_id in clients else "Unassigned",
                "budget_cents": row.budget_cents,
                "days": row.days,
                "daily_budget_cents": int(plan.get("daily_budget_cents", 0)),
                "bid_strategy": plan.get("bid_strategy", "—"),
                "sub_option": plan.get("sub_option", "—"),
                "template_name": plan.get("template_name", "—"),
                "keywords": keywords_by_campaign.get(row.id, []),
                "updated_at": row.updated_at,
            }
        )
    return output


@router.get("/marketing")
def marketing_page(request: Request, ctx: CurrentContext = Depends(require_context), db: Session = Depends(get_db)):
    base = _base_context(ctx, db)
    campaigns = _campaign_rows(ctx, db)
    return templates.TemplateResponse(
        request,
        "marketing.html",
        {
            **base,
            "platforms": PAID_PLATFORMS,
            "objectives": OBJECTIVES,
            "platform_objectives": PLATFORM_OBJECTIVES,
            "platform_config": PLATFORM_CONFIG,
            "campaigns": campaigns,
            "preview_plan": None,
            "preview_existing_keywords": [],
            "preview_added_keywords": [],
            "preview_client_id": None,
            "default_budget": 5000,
            "default_days": 7,
            "default_website_url": "",
            "default_social_handles": "",
            "preview_sub_option": "",
            "preview_template_name": "",
        },
    )


@router.post("/marketing/plan")
def preview_campaign_plan(
    request: Request,
    client_id: int = Form(...),
    platform: str = Form(...),
    objective: str = Form(...),
    budget: float = Form(...),
    days: int = Form(...),
    sub_option: str = Form(""),
    template_name: str = Form(""),
    existing_keywords: str = Form(""),
    website_url: str = Form(""),
    social_handles: str = Form(""),
    ctx: CurrentContext = Depends(require_context),
    db: Session = Depends(get_db),
):
    client = db.query(Client).filter(Client.id == client_id, Client.tenant_id == ctx.tenant.id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if platform not in PAID_PLATFORMS:
        raise HTTPException(status_code=400, detail="Unsupported ad platform")
    allowed_objectives = PLATFORM_OBJECTIVES.get(platform, OBJECTIVES)
    if objective not in allowed_objectives:
        raise HTTPException(status_code=400, detail="Objective not supported by this platform")
    allowed_sub_options = PLATFORM_CONFIG.get(platform, {}).get("sub_options", {}).get(objective, [])
    if sub_option and sub_option not in allowed_sub_options:
        raise HTTPException(status_code=400, detail="Sub-option not supported by this platform objective")
    allowed_templates = PLATFORM_CONFIG.get(platform, {}).get("templates", [])
    if template_name and template_name not in allowed_templates:
        raise HTTPException(status_code=400, detail="Template not supported by this platform")

    parsed_existing = parse_keywords(existing_keywords)
    parsed_handles = parse_handles(social_handles)
    website = normalize_website_url(website_url) or normalize_website_url(client.website_url)
    if not parsed_handles and client.social_handles:
        parsed_handles = parse_handles(client.social_handles)
    budget_cents = int(max(0.0, budget) * 100)
    plan = campaign_plan(
        platform,
        objective,
        budget_cents,
        max(1, days),
        client.name,
        parsed_existing,
        sub_option=sub_option or None,
        template_name=template_name or None,
    )
    plan["seo_content"] = seo_content_pack(client.name, website, parsed_handles, objective, plan["keywords_suggested"])
    added_keywords = [k for k in plan["keywords_suggested"] if k.lower() not in {e.lower() for e in parsed_existing}]

    base = _base_context(ctx, db)
    campaigns = _campaign_rows(ctx, db)
    return templates.TemplateResponse(
        request,
        "marketing.html",
        {
            **base,
            "platforms": PAID_PLATFORMS,
            "objectives": OBJECTIVES,
            "platform_objectives": PLATFORM_OBJECTIVES,
            "platform_config": PLATFORM_CONFIG,
            "campaigns": campaigns,
            "preview_plan": plan,
            "preview_existing_keywords": parsed_existing,
            "preview_added_keywords": added_keywords,
            "preview_client_id": client.id,
            "preview_platform": platform,
            "preview_objective": objective,
            "preview_sub_option": sub_option or plan.get("sub_option"),
            "preview_template_name": template_name or plan.get("template_name"),
            "default_budget": budget,
            "default_days": max(1, days),
            "default_website_url": website,
            "default_social_handles": ", ".join(parsed_handles),
        },
    )


@router.post("/marketing/campaigns")
def create_campaign(
    name: str = Form(...),
    client_id: int = Form(...),
    platform: str = Form(...),
    objective: str = Form(...),
    budget: float = Form(...),
    days: int = Form(...),
    sub_option: str = Form(""),
    template_name: str = Form(""),
    existing_keywords: str = Form(""),
    website_url: str = Form(""),
    social_handles: str = Form(""),
    ctx: CurrentContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    client = db.query(Client).filter(Client.id == client_id, Client.tenant_id == ctx.tenant.id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if platform not in PAID_PLATFORMS:
        raise HTTPException(status_code=400, detail="Unsupported ad platform")
    allowed_objectives = PLATFORM_OBJECTIVES.get(platform, OBJECTIVES)
    if objective not in allowed_objectives:
        raise HTTPException(status_code=400, detail="Objective not supported by this platform")
    allowed_sub_options = PLATFORM_CONFIG.get(platform, {}).get("sub_options", {}).get(objective, [])
    if sub_option and sub_option not in allowed_sub_options:
        raise HTTPException(status_code=400, detail="Sub-option not supported by this platform objective")
    allowed_templates = PLATFORM_CONFIG.get(platform, {}).get("templates", [])
    if template_name and template_name not in allowed_templates:
        raise HTTPException(status_code=400, detail="Template not supported by this platform")

    parsed_existing = parse_keywords(existing_keywords)
    parsed_handles = parse_handles(social_handles)
    website = normalize_website_url(website_url) or normalize_website_url(client.website_url)
    if not parsed_handles and client.social_handles:
        parsed_handles = parse_handles(client.social_handles)
    budget_cents = int(max(0.0, budget) * 100)
    plan = campaign_plan(
        platform,
        objective,
        budget_cents,
        max(1, days),
        client.name,
        parsed_existing,
        sub_option=sub_option or None,
        template_name=template_name or None,
    )
    plan["seo_content"] = seo_content_pack(client.name, website, parsed_handles, objective, plan["keywords_suggested"])

    campaign = MarketingCampaign(
        tenant_id=ctx.tenant.id,
        client_id=client.id,
        name=name.strip(),
        platform=platform,
        objective=objective,
        budget_cents=budget_cents,
        days=max(1, days),
        existing_keywords_json=json.dumps(parsed_existing),
        plan_json=json.dumps(plan),
    )
    db.add(campaign)
    db.flush()

    keywords_to_store = list(dict.fromkeys(parsed_existing + keyword_suggestions(client.name, objective, parsed_existing)))
    for keyword in keywords_to_store[:30]:
        source = "user" if keyword in parsed_existing else "suggested"
        db.add(MarketingKeyword(tenant_id=ctx.tenant.id, campaign_id=campaign.id, keyword=keyword, source=source))

    emit_event(
        db,
        tenant_id=ctx.tenant.id,
        event_type="marketing_campaign_created",
        entity_type="marketing_campaign",
        entity_id=campaign.id,
        severity="info",
        title=f"Marketing campaign planned: {campaign.name}",
        detail={"detail": f"{campaign.platform} · {campaign.objective}"},
    )
    audit_change(
        db,
        tenant_id=ctx.tenant.id,
        actor_user_id=ctx.user.id,
        entity_type="marketing_campaign",
        entity_id=campaign.id,
        action="create",
        before={},
        after={
            "name": campaign.name,
            "client_id": campaign.client_id,
            "platform": campaign.platform,
            "objective": campaign.objective,
            "budget_cents": campaign.budget_cents,
            "days": campaign.days,
            "website_url": website,
            "social_handles": parsed_handles,
        },
    )
    db.commit()
    return RedirectResponse(url=f"/marketing?tenant_id={ctx.tenant.id}&toast=campaign-created", status_code=303)
