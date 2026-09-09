"""Process-local coordination for permitted manual browser actions.

The gate only transports signals and serializable state.  Browser pages never
cross into HTTP request threads; the collector worker performs every recheck.
"""

from __future__ import annotations

import threading
from copy import deepcopy
from typing import Any, Callable

from src.runtime import iso_now


class ManualActionError(RuntimeError):
    """Base error for manual-action coordination."""


class ManualActionGenerationError(ManualActionError):
    """Raised when a browser button belongs to an older blocker generation."""


class ManualActionNotWaitingError(ManualActionError):
    """Raised when no active blocker can be acknowledged."""


class ManualActionGate:
    """Condition-backed, per-task signal state without any Playwright object."""

    def __init__(self) -> None:
        self._condition = threading.Condition(threading.RLock())
        self._states: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _public(state: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": state["status"],
            "generation": state["generation"],
            "reason": state["reason"],
            "requestedAt": state["requestedAt"],
            "lastCheckedAt": state["lastCheckedAt"],
            "attempt": state["attempt"],
            "canAcknowledge": (
                state["status"] == "waiting" and not state["acknowledged"]
            ),
        }

    def _idle(self) -> dict[str, Any]:
        return {
            "status": "idle",
            "generation": 0,
            "reason": None,
            "requestedAt": None,
            "lastCheckedAt": None,
            "attempt": 0,
            "acknowledged": False,
        }

    def snapshot(self, task_id: str) -> dict[str, Any]:
        with self._condition:
            return deepcopy(self._public(self._states.get(task_id, self._idle())))

    def request(self, task_id: str, reason: str) -> dict[str, Any]:
        normalized = str(reason or "").strip() or "淘宝需要人工操作"
        with self._condition:
            current = self._states.get(task_id)
            if current and current["status"] == "waiting" and not current["acknowledged"]:
                current["reason"] = normalized
                return deepcopy(self._public(current))
            generation = int((current or {}).get("generation") or 0) + 1
            state = {
                "status": "waiting",
                "generation": generation,
                "reason": normalized,
                "requestedAt": iso_now(),
                "lastCheckedAt": None,
                "attempt": int((current or {}).get("attempt") or 0),
                "acknowledged": False,
            }
            self._states[task_id] = state
            self._condition.notify_all()
            return deepcopy(self._public(state))

    def acknowledge(self, task_id: str, generation: int) -> dict[str, Any]:
        with self._condition:
            state = self._states.get(task_id)
            if state is None or state["status"] != "waiting":
                raise ManualActionNotWaitingError("当前任务没有等待中的淘宝人工验证")
            if generation != state["generation"]:
                raise ManualActionGenerationError("该验证提示已过期，请按最新提示重试")
            state["acknowledged"] = True
            self._condition.notify_all()
            return deepcopy(self._public(state))

    def wait(self, task_id: str, generation: int, timeout: float) -> bool:
        """Wait until acknowledged; false means the low-frequency timer elapsed."""

        with self._condition:
            self._condition.wait_for(
                lambda: (
                    task_id not in self._states
                    or self._states[task_id]["generation"] != generation
                    or self._states[task_id]["status"] != "waiting"
                    or self._states[task_id]["acknowledged"]
                ),
                timeout=max(0.0, timeout),
            )
            state = self._states.get(task_id)
            return bool(
                state
                and state["generation"] == generation
                and state["status"] == "waiting"
                and state["acknowledged"]
            )

    def mark_checked(
        self, task_id: str, generation: int, remaining_reason: str | None
    ) -> dict[str, Any]:
        with self._condition:
            state = self._states.get(task_id)
            if state is None or state["generation"] != generation:
                raise ManualActionGenerationError("人工验证状态已变化")
            state["lastCheckedAt"] = iso_now()
            state["attempt"] += 1
            if remaining_reason:
                state["reason"] = str(remaining_reason)
                if state["acknowledged"]:
                    state["generation"] += 1
                    state["requestedAt"] = iso_now()
                    state["acknowledged"] = False
                state["status"] = "waiting"
            else:
                state["status"] = "resolved"
                state["reason"] = None
                state["acknowledged"] = False
            self._condition.notify_all()
            return deepcopy(self._public(state))


class WebManualActionAdapter:
    """Collector-worker adapter; it alone is allowed to inspect the page."""

    def __init__(
        self,
        *,
        task_id: str,
        gate: ManualActionGate,
        blocker_checker: Callable[[Any], str | None],
        on_waiting: Callable[[dict[str, Any]], None],
        on_resolved: Callable[[dict[str, Any]], None],
        recheck_interval: float = 4.0,
    ) -> None:
        self.task_id = task_id
        self.gate = gate
        self.blocker_checker = blocker_checker
        self.on_waiting = on_waiting
        self.on_resolved = on_resolved
        self.recheck_interval = recheck_interval

    def wait(self, page: Any, reason: str, logger: Any) -> None:
        state = self.gate.request(self.task_id, reason)
        self.on_waiting(state)
        while True:
            generation = int(state["generation"])
            acknowledged = self.gate.wait(
                self.task_id, generation, timeout=self.recheck_interval
            )
            remaining = self.blocker_checker(page)
            next_state = self.gate.mark_checked(
                self.task_id, generation, remaining
            )
            if not remaining:
                logger.info("淘宝人工操作已由采集线程复检确认完成")
                self.on_resolved(next_state)
                return
            logger.warning(
                "页面仍被%s阻塞；%s后继续低频复检",
                remaining,
                "已收到人工确认，" if acknowledged else "",
            )
            if next_state["generation"] != generation:
                self.on_waiting(next_state)
            state = next_state
