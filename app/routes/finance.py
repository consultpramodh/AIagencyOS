from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import Membership, PersonalAccount, PersonalTransaction, SavingsGoal
from app.services.authz import CurrentContext, require_context, require_role

router = APIRouter(tags=["finance"])
templates = Jinja2Templates(directory="app/templates")


def _to_cents(amount: float) -> int:
    return int(round(max(amount, 0.0) * 100))


def _base_context(ctx: CurrentContext, db: Session) -> dict:
    memberships = db.query(Membership).filter(Membership.user_id == ctx.user.id).all()
    return {"ctx": ctx, "memberships": memberships}


@router.get("/finance")
def finance_page(request: Request, ctx: CurrentContext = Depends(require_context), db: Session = Depends(get_db)):
    base = _base_context(ctx, db)
    accounts = db.query(PersonalAccount).filter(PersonalAccount.tenant_id == ctx.tenant.id).order_by(PersonalAccount.id.asc()).all()
    goals = db.query(SavingsGoal).filter(SavingsGoal.tenant_id == ctx.tenant.id).order_by(SavingsGoal.priority.asc(), SavingsGoal.id.asc()).all()
    transactions = (
        db.query(PersonalTransaction)
        .filter(PersonalTransaction.tenant_id == ctx.tenant.id)
        .order_by(PersonalTransaction.transaction_date.desc(), PersonalTransaction.id.desc())
        .limit(20)
        .all()
    )

    income_cents = sum(t.amount_cents for t in transactions if t.transaction_kind == "income")
    expense_cents = sum(t.amount_cents for t in transactions if t.transaction_kind == "expense")
    invested_cents = sum(t.amount_cents for t in transactions if t.transaction_kind == "investment")
    net_cents = income_cents - expense_cents - invested_cents
    total_balance_cents = sum(a.balance_cents for a in accounts)
    goal_target_cents = sum(g.target_cents for g in goals)
    goal_current_cents = sum(g.current_cents for g in goals)

    account_names = {account.id: account.name for account in accounts}

    return templates.TemplateResponse(
        "finance.html",
        {
            "request": request,
            **base,
            "accounts": accounts,
            "goals": goals,
            "transactions": transactions,
            "account_names": account_names,
            "income_cents": income_cents,
            "expense_cents": expense_cents,
            "invested_cents": invested_cents,
            "net_cents": net_cents,
            "total_balance_cents": total_balance_cents,
            "goal_target_cents": goal_target_cents,
            "goal_current_cents": goal_current_cents,
        },
    )


@router.post("/finance/accounts")
def create_account(
    name: str = Form(...),
    account_type: str = Form(...),
    institution: str = Form(""),
    balance: float = Form(0.0),
    ctx: CurrentContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    db.add(
        PersonalAccount(
            tenant_id=ctx.tenant.id,
            name=name.strip(),
            account_type=account_type.strip() or "checking",
            institution=institution.strip(),
            balance_cents=_to_cents(balance),
        )
    )
    db.commit()
    return RedirectResponse(url=f"/finance?tenant_id={ctx.tenant.id}", status_code=303)


@router.post("/finance/transactions")
def create_transaction(
    account_id: int = Form(...),
    transaction_date: str = Form(...),
    category: str = Form(...),
    description: str = Form(""),
    amount: float = Form(...),
    transaction_kind: str = Form(...),
    ctx: CurrentContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    account = (
        db.query(PersonalAccount)
        .filter(PersonalAccount.id == account_id, PersonalAccount.tenant_id == ctx.tenant.id)
        .first()
    )
    if not account:
        return RedirectResponse(url=f"/finance?tenant_id={ctx.tenant.id}", status_code=303)

    amount_cents = _to_cents(amount)
    kind = (transaction_kind or "expense").strip().lower()
    if kind not in {"income", "expense", "investment"}:
        kind = "expense"

    if kind == "income":
        account.balance_cents += amount_cents
    else:
        account.balance_cents -= amount_cents

    db.add(
        PersonalTransaction(
            tenant_id=ctx.tenant.id,
            account_id=account.id,
            transaction_date=date.fromisoformat(transaction_date),
            category=category.strip() or "general",
            description=description.strip(),
            amount_cents=amount_cents,
            transaction_kind=kind,
        )
    )
    db.commit()
    return RedirectResponse(url=f"/finance?tenant_id={ctx.tenant.id}", status_code=303)


@router.post("/finance/goals")
def create_goal(
    title: str = Form(...),
    target_amount: float = Form(...),
    current_amount: float = Form(0.0),
    target_date: str = Form(""),
    priority: str = Form("medium"),
    ctx: CurrentContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    goal_date = date.fromisoformat(target_date) if target_date else None
    db.add(
        SavingsGoal(
            tenant_id=ctx.tenant.id,
            title=title.strip(),
            target_cents=_to_cents(target_amount),
            current_cents=_to_cents(current_amount),
            target_date=goal_date,
            priority=priority.strip() or "medium",
        )
    )
    db.commit()
    return RedirectResponse(url=f"/finance?tenant_id={ctx.tenant.id}", status_code=303)
