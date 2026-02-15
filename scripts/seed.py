import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.db import SessionLocal
from app.core.security import hash_password
from datetime import date

from app.models import (
    Approval,
    AgentRegistry,
    BrainstormQA,
    BrainstormSession,
    CalendarEvent,
    Client,
    ClientFinancial,
    ConnectorCredential,
    ConnectorInstance,
    ConnectorRun,
    ConnectorType,
    Contact,
    Deal,
    DealStage,
    Event,
    Membership,
    MarketingCampaign,
    MarketingKeyword,
    Note,
    Project,
    ServiceJob,
    Task,
    Tenant,
    User,
    WorkflowRun,
    WorkflowStep,
    WorkflowTemplate,
)


def run() -> None:
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == "owner@demo.local").first():
            print("Seed already applied")
            return

        tenant_a = Tenant(name="Demo Agency")
        tenant_b = Tenant(name="Second Brand")
        db.add_all([tenant_a, tenant_b])
        db.flush()

        owner = User(email="owner@demo.local", full_name="Demo Owner", password_hash=hash_password("demo1234"))
        viewer = User(email="viewer@demo.local", full_name="Demo Viewer", password_hash=hash_password("demo1234"))
        db.add_all([owner, viewer])
        db.flush()

        db.add_all(
            [
                Membership(tenant_id=tenant_a.id, user_id=owner.id, role="owner"),
                Membership(tenant_id=tenant_b.id, user_id=owner.id, role="admin"),
                Membership(tenant_id=tenant_a.id, user_id=viewer.id, role="viewer"),
            ]
        )
        db.flush()

        client = Client(
            tenant_id=tenant_a.id,
            name="Acme Plumbing",
            contact_name="Mike Carter",
            contact_email="mike@acmeplumbing.example",
            contact_phone="+14155550111",
            website_url="https://acmeplumbing.example",
            social_handles="@acmeplumbing, @acmeplumbing_help",
            status="active",
        )
        db.add(client)
        db.flush()

        project = Project(tenant_id=tenant_a.id, client_id=client.id, name="Local SEO Sprint", status="planning")
        db.add(project)
        db.flush()

        note = Note(
            tenant_id=tenant_a.id,
            project_id=project.id,
            created_by_user_id=owner.id,
            title="Kickoff Notes",
            body_markdown="# Goals\n- Improve local rankings\n- Launch landing page updates",
        )
        db.add(note)

        task = Task(
            tenant_id=tenant_a.id,
            project_id=project.id,
            created_by_user_id=owner.id,
            title="Prepare weekly report",
            description="Draft first weekly snapshot for client review",
            status="todo",
            due_date=date.today(),
        )
        db.add(task)

        db.add(
            ServiceJob(
                tenant_id=tenant_a.id,
                client_id=client.id,
                project_id=project.id,
                created_by_user_id=owner.id,
                title="Monthly SEO Maintenance",
                service_type="SEO",
                stage="scheduled",
                scheduled_for=date.today(),
                notes="Review rankings and update GBP posts",
            )
        )

        db.add(
            CalendarEvent(
                tenant_id=tenant_a.id,
                created_by_user_id=owner.id,
                title="Client Review Call",
                event_date=date.today(),
                notes="Share KPI updates",
            )
        )

        stage_lead = DealStage(tenant_id=tenant_a.id, name="Lead", position=1, is_won=False, is_lost=False)
        stage_qualified = DealStage(tenant_id=tenant_a.id, name="Qualified", position=2, is_won=False, is_lost=False)
        stage_won = DealStage(tenant_id=tenant_a.id, name="Won", position=3, is_won=True, is_lost=False)
        db.add_all([stage_lead, stage_qualified, stage_won])
        db.flush()

        contact = Contact(
            tenant_id=tenant_a.id,
            client_id=client.id,
            name="Mike Carter",
            email="mike@acmeplumbing.example",
            phone="+14155550111",
            role_title="Owner",
        )
        db.add(contact)
        db.flush()

        deal = Deal(
            tenant_id=tenant_a.id,
            client_id=client.id,
            contact_id=contact.id,
            project_id=project.id,
            stage_id=stage_qualified.id,
            title="Q2 Growth Retainer",
            value_cents=350000,
            close_date=date.today(),
            probability_pct=70,
            status="open",
        )
        db.add(deal)
        db.add(
            ClientFinancial(
                tenant_id=tenant_a.id,
                client_id=client.id,
                mrr_cents=120000,
                retainer_cents=120000,
                last_invoice_cents=120000,
                cogs_estimate_cents=45000,
                renewal_date=date.today(),
            )
        )

        db.add_all(
            [
                AgentRegistry(
                    tenant_id=tenant_a.id,
                    agent_key="strategy_lead",
                    name="Strategy Lead",
                    responsibilities="Owns campaign strategy and approvals",
                    allowed_actions_json='["plan","approve"]',
                    enabled=True,
                    default_mode="A",
                    escalation_rules_json='{"to":"owner"}',
                ),
                AgentRegistry(
                    tenant_id=tenant_a.id,
                    agent_key="reporting_ops",
                    name="Reporting Ops",
                    responsibilities="Builds recurring KPI reporting",
                    allowed_actions_json='["report"]',
                    enabled=True,
                    default_mode="B",
                    escalation_rules_json='{"to":"strategy_lead"}',
                ),
            ]
        )

        wf = WorkflowTemplate(
            tenant_id=tenant_a.id,
            name="Weekly Client Reporting",
            description="Collect numbers and prepare review summary",
            version=1,
            created_by_user_id=owner.id,
        )
        db.add(wf)
        db.flush()
        db.add_all(
            [
                WorkflowStep(
                    tenant_id=tenant_a.id,
                    workflow_id=wf.id,
                    step_order=1,
                    name="Collect source metrics",
                    action_type="fetch_metrics",
                    agent_key="reporting_ops",
                    config_json="{}",
                    gating_policy="auto",
                ),
                WorkflowStep(
                    tenant_id=tenant_a.id,
                    workflow_id=wf.id,
                    step_order=2,
                    name="Draft weekly summary",
                    action_type="draft_summary",
                    agent_key="strategy_lead",
                    config_json="{}",
                    gating_policy="approve",
                ),
            ]
        )
        seeded_run = WorkflowRun(
            tenant_id=tenant_a.id,
            workflow_id=wf.id,
            status="blocked",
            triggered_by_user_id=owner.id,
            client_id=client.id,
            project_id=project.id,
        )
        db.add(seeded_run)
        db.flush()
        db.add(
            Approval(
                tenant_id=tenant_a.id,
                client_id=client.id,
                project_id=project.id,
                workflow_run_id=seeded_run.id,
                status="pending",
                title="Landing page draft approval",
                requested_by_user_id=owner.id,
            )
        )
        db.add(
            Event(
                tenant_id=tenant_a.id,
                type="workflow_run_blocked",
                entity_type="workflow_run",
                entity_id=seeded_run.id,
                severity="high",
                title="Blocked workflow requires approval",
                detail_json='{"detail":"Awaiting signoff"}',
            )
        )

        session = BrainstormSession(
            tenant_id=tenant_a.id,
            title="Grow monthly leads for local services",
            status="active",
            created_by_user_id=owner.id,
        )
        db.add(session)
        db.flush()
        db.add_all(
            [
                BrainstormQA(tenant_id=tenant_a.id, session_id=session.id, question_order=1, question="What is your 90-day outcome?", answer="30% more qualified leads"),
                BrainstormQA(tenant_id=tenant_a.id, session_id=session.id, question_order=2, question="What channels matter most?", answer="SEO and Ads"),
            ]
        )

        ga4 = ConnectorType(key="ga4", name="Google Analytics 4")
        email = ConnectorType(key="email", name="Email Provider")
        db.add_all([ga4, email])
        db.flush()
        inst = ConnectorInstance(
            tenant_id=tenant_a.id,
            connector_type_id=ga4.id,
            name="GA4 Manual",
            mode="manual",
            status="active",
            config_json="{}",
        )
        db.add(inst)
        db.flush()
        db.add(ConnectorCredential(tenant_id=tenant_a.id, connector_instance_id=inst.id, secret_masked="configured-manual", is_configured=True))
        db.add(ConnectorRun(tenant_id=tenant_a.id, connector_instance_id=inst.id, status="succeeded", log="Seed run"))

        campaign = MarketingCampaign(
            tenant_id=tenant_a.id,
            client_id=client.id,
            name="Acme Plumbing Leads - Search",
            platform="Google Ads",
            objective="Lead Generation",
            budget_cents=5000,
            days=7,
            existing_keywords_json='["acme plumbing", "emergency plumber"]',
            plan_json='{"daily_budget_cents":715,"bid_strategy":"Maximize Conversions","recommended_networks":"Search + Retargeting","audience_setup":"Intent keywords + remarketing list","keywords_suggested":["acme plumbing near me","emergency plumber quote"]}',
        )
        db.add(campaign)
        db.flush()
        db.add_all(
            [
                MarketingKeyword(tenant_id=tenant_a.id, campaign_id=campaign.id, keyword="acme plumbing", source="user"),
                MarketingKeyword(tenant_id=tenant_a.id, campaign_id=campaign.id, keyword="emergency plumber", source="user"),
                MarketingKeyword(tenant_id=tenant_a.id, campaign_id=campaign.id, keyword="acme plumbing near me", source="suggested"),
            ]
        )

        db.commit()
        print("Seeded demo tenant/user/client/project")
    finally:
        db.close()


if __name__ == "__main__":
    run()
