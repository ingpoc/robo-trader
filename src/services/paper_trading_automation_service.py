"""Local orchestration for Codex-backed paper-trading automation runs."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

from src.auth.ai_runtime_auth import get_ai_runtime_status
from src.models.paper_trading_automation import AutomationControlState, AutomationJobControl, AutomationJobType, AutomationRunRecord

logger = logging.getLogger(__name__)


class AutomationPausedError(RuntimeError):
    """Raised when automation is paused globally or for a specific job."""


class DuplicateAutomationRunError(RuntimeError):
    """Raised when a run of the same job is already active."""


class PaperTradingAutomationService:
    """Backend-owned local automation orchestration for Codex-backed jobs."""

    DEFAULT_SCHEDULE_MINUTES: Dict[str, int] = {
        "research_cycle": 60,
        "decision_review_cycle": 15,
        "exit_check_cycle": 15,
        "daily_review_cycle": 1440,
        "improvement_eval_cycle": 360,
    }

    def __init__(self, store, *, project_dir: str):
        self.store = store
        self.project_dir = Path(project_dir)
        self.run_dir = self.project_dir / "run"
        self._tasks: Dict[str, asyncio.Task] = {}
        self._task_lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Ensure default automation controls exist."""
        self.run_dir.mkdir(parents=True, exist_ok=True)
        for job_type, schedule_minutes in self.DEFAULT_SCHEDULE_MINUTES.items():
            existing = await self.store.get_automation_job_control(job_type)
            if existing:
                continue
            control = AutomationJobControl(job_type=job_type, schedule_minutes=schedule_minutes)
            control.advance_next_run()
            await self.store.upsert_automation_job_control(
                {
                    **control.to_store_dict(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )

    async def get_control_state(self) -> AutomationControlState:
        """Return combined global + per-job automation control state."""
        global_pause = await self.store.get_automation_global_pause()
        controls = [AutomationJobControl(**item) for item in await self.store.list_automation_job_controls()]
        return AutomationControlState(
            global_pause=bool(global_pause.get("paused", False)),
            paused_job_types=[control.job_type for control in controls if control.paused_at or not control.enabled],
            updated_at=global_pause.get("updated_at") or datetime.now(timezone.utc).isoformat(),
            controls=controls,
        )

    async def pause(self, *, job_types: Optional[List[AutomationJobType]] = None, reason: str = "") -> AutomationControlState:
        """Pause automation globally or for specific job types."""
        now = datetime.now(timezone.utc).isoformat()
        if not job_types:
            await self.store.set_automation_global_pause(True, reason=reason)
            return await self.get_control_state()

        for job_type in job_types:
            existing = await self.store.get_automation_job_control(job_type) or {
                "job_type": job_type,
                "enabled": True,
                "schedule_minutes": self.DEFAULT_SCHEDULE_MINUTES[job_type],
                "last_run_at": None,
                "next_run_at": None,
            }
            existing.update({"paused_at": now, "pause_reason": reason, "updated_at": now})
            await self.store.upsert_automation_job_control(existing)
        return await self.get_control_state()

    async def resume(self, *, job_types: Optional[List[AutomationJobType]] = None) -> AutomationControlState:
        """Resume automation globally or for specific job types."""
        now = datetime.now(timezone.utc).isoformat()
        if not job_types:
            await self.store.set_automation_global_pause(False, reason="")
            return await self.get_control_state()

        for job_type in job_types:
            existing = await self.store.get_automation_job_control(job_type) or {
                "job_type": job_type,
                "enabled": True,
                "schedule_minutes": self.DEFAULT_SCHEDULE_MINUTES[job_type],
                "last_run_at": None,
                "next_run_at": None,
            }
            existing.update({"paused_at": None, "pause_reason": "", "updated_at": now})
            await self.store.upsert_automation_job_control(existing)
        return await self.get_control_state()

    async def submit_run(
        self,
        *,
        account_id: str,
        job_type: AutomationJobType,
        input_payload: Dict[str, Any],
        timeout_seconds: float,
        trigger_reason: str,
        schedule_source: str,
        execute: Callable[[], Awaitable[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """Create and start a local automation run."""
        await self._assert_not_paused(job_type)
        active = await self.store.get_active_automation_run(account_id, job_type)
        if active:
            raise DuplicateAutomationRunError(
                f"{job_type} already has an active run ({active['run_id']})."
            )

        now = datetime.now(timezone.utc)
        run_id = f"autorun_{job_type}_{now.strftime('%Y%m%d%H%M%S')}_{hashlib.md5((account_id + job_type + now.isoformat()).encode()).hexdigest()[:6]}"
        started_at = now.isoformat()
        record = AutomationRunRecord(
            run_id=run_id,
            account_id=account_id,
            job_type=job_type,
            status="queued",
            schedule_source=schedule_source,
            trigger_reason=trigger_reason,
            input_digest=self._input_digest(input_payload),
            started_at=started_at,
            timeout_at=(now + timedelta(seconds=timeout_seconds)).isoformat(),
        )
        await self.store.create_automation_run(record.to_store_dict())

        async with self._task_lock:
            self._tasks[run_id] = asyncio.create_task(
                self._run_task(run_id=run_id, job_type=job_type, execute=execute, timeout_seconds=timeout_seconds),
                name=f"automation:{run_id}",
            )

        return await self.store.get_automation_run(run_id) or record.to_store_dict()

    async def cancel_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Cancel an active automation run if it is still executing."""
        async with self._task_lock:
            task = self._tasks.get(run_id)
            if task and not task.done():
                task.cancel()
        return await self.store.get_automation_run(run_id)

    async def list_runs(self, account_id: str, *, limit: int = 20) -> List[Dict[str, Any]]:
        return await self.store.list_automation_runs(account_id, limit=limit)

    async def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        return await self.store.get_automation_run(run_id)

    async def get_runtime_readiness(self) -> Dict[str, Any]:
        """Return a provider-native view of Codex subscription runtime readiness."""
        status = await get_ai_runtime_status(force_refresh=False)
        return {
            "status": "ready" if status.is_valid else ("degraded" if status.authenticated else "blocked"),
            "provider": status.provider,
            "authenticated": status.authenticated,
            "model": status.model,
            "checked_at": status.checked_at,
            "error": status.error,
            "last_successful_validation_at": status.account_info.get("last_successful_validation_at"),
            "usage_limited": bool((status.rate_limit_info or {}).get("status") == "exhausted"),
            "metadata": status.metadata,
        }

    async def _run_task(
        self,
        *,
        run_id: str,
        job_type: str,
        execute: Callable[[], Awaitable[Dict[str, Any]]],
        timeout_seconds: float,
    ) -> None:
        started_at = datetime.now(timezone.utc)
        await self.store.update_automation_run(
            run_id,
            {"status": "in_progress", "updated_at": started_at.isoformat()},
        )
        status = "error"
        status_reason = "Automation run raised an unhandled exception."
        payload: Dict[str, Any] = {}
        try:
            payload = await asyncio.wait_for(execute(), timeout=timeout_seconds)
            status = str(payload.get("status") or "error")
            blockers = list(payload.get("blockers") or [])
            status_reason = blockers[0] if blockers else (payload.get("status_reason") or "Automation run completed.")
        except asyncio.CancelledError:
            status = "cancelled"
            status_reason = "Automation run was cancelled."
            payload = {"status": status, "blockers": [status_reason]}
        except asyncio.TimeoutError:
            status = "blocked"
            status_reason = f"Automation run exceeded the {int(timeout_seconds)}s deadline and was cancelled."
            payload = {"status": status, "blockers": [status_reason]}
        except Exception as exc:
            logger.exception("automation_run_failed run_id=%s job_type=%s", run_id, job_type)
            status_reason = str(exc).strip() or status_reason
            payload = {"status": status, "blockers": [status_reason]}

        completed_at = datetime.now(timezone.utc)
        artifact_path = await self._write_artifact(
            run_id=run_id,
            job_type=job_type,
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
            payload=payload,
        )
        duration_ms = max(int((completed_at - started_at).total_seconds() * 1000), 0)
        provider_metadata = dict(payload.get("provider_metadata") or {})
        await self.store.update_automation_run(
            run_id,
            {
                "status": status,
                "status_reason": status_reason,
                "block_reason": status_reason if status in {"blocked", "error", "cancelled"} else "",
                "provider_metadata": provider_metadata,
                "tool_trace": self._tool_trace_for_payload(payload),
                "artifact_path": str(artifact_path),
                "completed_at": completed_at.isoformat(),
                "duration_ms": duration_ms,
                "updated_at": completed_at.isoformat(),
            },
        )
        run = await self.store.get_automation_run(run_id)
        if run:
            await self._advance_job_control(job_type, completed_at=completed_at.isoformat())
        async with self._task_lock:
            self._tasks.pop(run_id, None)

    async def _assert_not_paused(self, job_type: str) -> None:
        global_pause = await self.store.get_automation_global_pause()
        if global_pause.get("paused"):
            raise AutomationPausedError(global_pause.get("reason") or "Automation is globally paused.")
        job_control = await self.store.get_automation_job_control(job_type)
        if job_control and job_control.get("paused_at"):
            raise AutomationPausedError(job_control.get("pause_reason") or f"{job_type} is paused.")

    async def _advance_job_control(self, job_type: str, *, completed_at: str) -> None:
        existing = await self.store.get_automation_job_control(job_type)
        if not existing:
            control = AutomationJobControl(job_type=job_type, schedule_minutes=self.DEFAULT_SCHEDULE_MINUTES[job_type])
        else:
            control = AutomationJobControl(**existing)
        control.last_run_at = completed_at
        control.advance_next_run(from_timestamp=completed_at)
        control.paused_at = existing.get("paused_at") if existing else None
        control.pause_reason = existing.get("pause_reason", "") if existing else ""
        await self.store.upsert_automation_job_control(
            {
                **control.to_store_dict(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    def _input_digest(self, payload: Dict[str, Any]) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()

    async def _write_artifact(
        self,
        *,
        run_id: str,
        job_type: str,
        started_at: str,
        completed_at: str,
        payload: Dict[str, Any],
    ) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        path = self.run_dir / f"{job_type}-{timestamp}.md"
        lines = [
            "# Automation Run Artifact",
            "",
            f"- Run ID: `{run_id}`",
            f"- Job Type: `{job_type}`",
            f"- Started At: `{started_at}`",
            f"- Completed At: `{completed_at}`",
            f"- Status: `{payload.get('status', 'error')}`",
        ]
        blockers = list(payload.get("blockers") or [])
        if blockers:
            lines.append(f"- Top Blocker: `{blockers[0]}`")
        lines.extend([
            "",
            "## Payload",
            "",
            "```json",
            json.dumps(payload, indent=2, sort_keys=True, default=str),
            "```",
            "",
        ])
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    @staticmethod
    def _tool_trace_for_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        provider_metadata = dict(payload.get("provider_metadata") or {})
        tools = list(provider_metadata.get("tools") or [])
        if not tools:
            return []
        return [{"tool": tool} if not isinstance(tool, dict) else tool for tool in tools]
