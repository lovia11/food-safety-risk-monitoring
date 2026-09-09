import logging
import threading
import time
import unittest

from src.manual_action_gate import (
    ManualActionGate,
    ManualActionGenerationError,
    WebManualActionAdapter,
)


class ManualActionGateTest(unittest.TestCase):
    def test_generation_repeated_acknowledge_and_stale_generation(self):
        gate = ManualActionGate()
        first = gate.request("task-1", "淘宝人工验证")
        self.assertEqual(first["generation"], 1)
        self.assertTrue(first["canAcknowledge"])

        acknowledged = gate.acknowledge("task-1", 1)
        self.assertFalse(acknowledged["canAcknowledge"])
        self.assertEqual(gate.acknowledge("task-1", 1)["generation"], 1)

        second = gate.mark_checked("task-1", 1, "淘宝人工验证")
        self.assertEqual(second["generation"], 2)
        self.assertTrue(second["canAcknowledge"])
        with self.assertRaises(ManualActionGenerationError):
            gate.acknowledge("task-1", 1)

    def test_acknowledge_wakes_waiter_immediately(self):
        gate = ManualActionGate()
        gate.request("task-1", "淘宝登录")
        result = []
        started = threading.Event()

        def wait_for_signal():
            started.set()
            result.append(gate.wait("task-1", 1, timeout=2.0))

        worker = threading.Thread(target=wait_for_signal)
        worker.start()
        self.assertTrue(started.wait(0.5))
        began = time.monotonic()
        gate.acknowledge("task-1", 1)
        worker.join(0.5)
        self.assertFalse(worker.is_alive())
        self.assertTrue(result[0])
        self.assertLess(time.monotonic() - began, 0.5)

    def test_web_adapter_rechecks_only_on_worker_and_requires_second_ack(self):
        gate = ManualActionGate()
        checks = []
        waiting_generations = []
        worker_id = []
        check_results = iter(["淘宝人工验证", None])

        def check(page):
            checks.append((threading.get_ident(), page))
            return next(check_results)

        adapter = WebManualActionAdapter(
            task_id="task-1",
            gate=gate,
            blocker_checker=check,
            on_waiting=lambda state: waiting_generations.append(state["generation"]),
            on_resolved=lambda _state: None,
            recheck_interval=30,
        )

        def collect():
            worker_id.append(threading.get_ident())
            adapter.wait(object(), "淘宝人工验证", logging.getLogger("test"))

        worker = threading.Thread(target=collect)
        worker.start()
        deadline = time.monotonic() + 1
        while gate.snapshot("task-1")["generation"] != 1 and time.monotonic() < deadline:
            time.sleep(0.005)
        gate.acknowledge("task-1", 1)
        deadline = time.monotonic() + 1
        while gate.snapshot("task-1")["generation"] != 2 and time.monotonic() < deadline:
            time.sleep(0.005)
        self.assertTrue(worker.is_alive())
        gate.acknowledge("task-1", 2)
        worker.join(1)

        self.assertFalse(worker.is_alive())
        self.assertEqual(waiting_generations, [1, 2])
        self.assertEqual(len(checks), 2)
        self.assertTrue(all(thread_id == worker_id[0] for thread_id, _page in checks))
        self.assertEqual(gate.snapshot("task-1")["status"], "resolved")


if __name__ == "__main__":
    unittest.main()
