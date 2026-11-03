"""Local HTTP business app used to test an Agent against a real interface."""
from __future__ import annotations

import os
from html import escape

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from workflow_env import RefundTask, RefundWorkflowEnv

app = FastAPI(title="Refund Operations Sandbox")
_amount = float(os.getenv("REFUND_AMOUNT", "900"))
_days = int(os.getenv("REFUND_DAYS", "7"))
_failure = os.getenv("REFUND_FAILURE", "find_order") or None
env = RefundWorkflowEnv(RefundTask("WEB-1", "ORDER-1", "CUSTOMER-1", _amount, _days, "damaged"), _failure)
env.reset()


class ActionRequest(BaseModel):
    action: str


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    state = env.observe()
    buttons = "".join(f"<button data-action='{a}' onclick=\"doAction('{a}')\">{a}</button>" for a in ["find_customer", "find_order", "check_policy", "draft_refund", "submit_refund", "request_approval", "recover"])
    return f"""<!doctype html><html><head><title>Refund Sandbox</title></head>
    <body><h1>Refund Operations Sandbox</h1>
    <p id='status'>Status: {escape(state['status'])}</p>
    <p id='risk'>Requires approval: {state['requires_approval']}</p>
    <pre id='state-json'></pre><div id='actions'>{buttons}</div>
    <p>This local page is an oracle-backed business UI for Agent integration tests.</p>
    <script>
    async function refresh() {{ const r = await fetch('/state'); const x = await r.json();
      document.getElementById('status').textContent = 'Status: ' + x.status;
      document.getElementById('risk').textContent = 'Requires approval: ' + x.requires_approval;
      document.getElementById('state-json').textContent = JSON.stringify(x);
    }}
    async function doAction(action) {{ await fetch('/action', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{action}})}}); await refresh(); }}
    refresh();
    </script></body></html>"""


@app.get("/state")
def state() -> dict:
    return env.observe() | {"events": env.state.events, "terminal": env.state.status.value in {"submitted", "human_handoff", "failed"}}


@app.post("/action")
def action(request: ActionRequest) -> dict:
    obs, reward, done, info = env.step(request.action)
    return {"observation": obs, "reward": reward, "done": done, "info": info, "events": env.state.events}


@app.post("/reset")
def reset(
    amount: float | None = Query(default=None, gt=0),
    days: int | None = Query(default=None, ge=0),
    failure: str | None = Query(default=None),
) -> dict:
    """Reset with a new task so the HTTP layer can run a real benchmark."""
    global env
    if amount is not None or days is not None or failure is not None:
        current = env.task
        env = RefundWorkflowEnv(
            RefundTask(
                current.task_id,
                current.order_id,
                current.customer_id,
                amount if amount is not None else current.amount,
                days if days is not None else current.days_since_purchase,
                current.reason,
            ),
            None if failure in {None, "", "none"} else failure,
        )
    return env.reset() | {"events": env.state.events}
