"""Tests deterministes des simulateurs d'ordonnancement et de memoire."""

from __future__ import annotations

import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


# Les tests restent executables aussi bien depuis ``code/`` que depuis la
# racine du livrable avec ``python3 -m unittest discover``.
CODE_ROOT = Path(__file__).resolve().parents[1]
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from esinos.memory import (  # noqa: E402
    VirtualMemoryError,
    VirtualMemoryManager,
    parse_references,
    simulate_page_replacement,
)
from esinos.cli import main  # noqa: E402
from esinos.scheduler import (  # noqa: E402
    Process,
    SchedulerError,
    parse_processes,
    run_scheduler,
)


def timeline_as_tuples(result):
    """Normalise le Gantt pour que les assertions restent tres lisibles."""

    return [(slice_.label, slice_.start, slice_.end) for slice_ in result.timeline]


class ProcessAndSchedulerTests(unittest.TestCase):
    def test_process_and_parser_validate_the_input_format(self):
        parsed = parse_processes(" P1:0:3:2, P2:1:2 ")

        self.assertEqual(
            parsed,
            [Process("P1", arrival=0, burst=3, priority=2), Process("P2", 1, 2, 0)],
        )
        with self.assertRaises(SchedulerError):
            Process("", arrival=0, burst=1)
        with self.assertRaises(SchedulerError):
            parse_processes("P1:0:0")

    def test_fcfs_includes_idle_time_and_correct_metrics(self):
        result = run_scheduler(
            [Process("P1", 2, 2), Process("P2", 4, 1)], "fcfs"
        )

        self.assertEqual(
            timeline_as_tuples(result),
            [("IDLE", 0, 2), ("P1", 2, 4), ("P2", 4, 5)],
        )
        metrics = {item.pid: item for item in result.metrics}
        self.assertEqual((metrics["P1"].waiting, metrics["P1"].turnaround), (0, 2))
        self.assertEqual((metrics["P2"].waiting, metrics["P2"].turnaround), (0, 1))
        self.assertEqual(result.average_waiting, 0.0)

    def test_sjf_selects_the_shortest_ready_process(self):
        processes = [Process("P1", 0, 3), Process("P2", 1, 2), Process("P3", 2, 1)]
        result = run_scheduler(processes, "sjf")

        self.assertEqual(
            timeline_as_tuples(result),
            [("P1", 0, 3), ("P3", 3, 4), ("P2", 4, 6)],
        )
        metrics = {item.pid: item for item in result.metrics}
        self.assertEqual(metrics["P3"].waiting, 1)
        self.assertAlmostEqual(result.average_turnaround, 10 / 3)

    def test_round_robin_honours_quantum_and_arrivals_at_slice_end(self):
        processes = [Process("P1", 0, 3), Process("P2", 1, 2), Process("P3", 2, 1)]
        result = run_scheduler(processes, "rr", quantum=2)

        self.assertEqual(result.quantum, 2)
        self.assertEqual(
            timeline_as_tuples(result),
            [("P1", 0, 2), ("P2", 2, 4), ("P3", 4, 5), ("P1", 5, 6)],
        )
        metrics = {item.pid: item for item in result.metrics}
        self.assertEqual((metrics["P1"].completion, metrics["P1"].waiting), (6, 3))
        self.assertEqual((metrics["P2"].completion, metrics["P2"].waiting), (4, 1))
        self.assertEqual((metrics["P3"].completion, metrics["P3"].waiting), (5, 2))
        self.assertEqual(result.average_waiting, 2.0)

    def test_priority_uses_lowest_numeric_value_first(self):
        processes = [
            Process("P1", 0, 2, priority=2),
            Process("P2", 0, 1, priority=1),
            Process("P3", 0, 1, priority=0),
        ]
        result = run_scheduler(processes, "priority")

        self.assertEqual(
            timeline_as_tuples(result),
            [("P3", 0, 1), ("P2", 1, 2), ("P1", 2, 4)],
        )
        self.assertEqual(result.algorithm, "Priority (non preemptif)")
        self.assertEqual(result.average_waiting, 1.0)


class PageReplacementTests(unittest.TestCase):
    def test_parse_references_accepts_commas_and_semicolons(self):
        self.assertEqual(parse_references("7, 0; 1,2"), [7, 0, 1, 2])
        with self.assertRaises(VirtualMemoryError):
            parse_references("1,,2")

    def test_fifo_records_hits_frames_and_evicted_page(self):
        result = simulate_page_replacement([1, 2, 3, 1, 4], 3, "fifo")

        self.assertEqual(result.algorithm, "FIFO")
        self.assertEqual(result.page_faults, 4)
        self.assertEqual(result.hits, 1)
        self.assertTrue(result.steps[3].hit)
        self.assertEqual(result.steps[3].frames, (1, 2, 3))
        self.assertEqual((result.steps[4].evicted, result.steps[4].frames), (1, (4, 2, 3)))

    def test_fifo_lru_and_optimal_have_known_fault_counts(self):
        references = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]

        fifo = simulate_page_replacement(references, 3, "fifo")
        lru = simulate_page_replacement(references, 3, "lru")
        optimal = simulate_page_replacement(references, 3, "optimal")

        self.assertEqual((fifo.page_faults, lru.page_faults, optimal.page_faults), (9, 10, 7))
        self.assertEqual(optimal.hits, 5)
        self.assertLess(optimal.page_faults, fifo.page_faults)


class VirtualMemoryManagerTests(unittest.TestCase):
    def test_translation_tlb_lru_and_effective_access_time(self):
        manager = VirtualMemoryManager(
            page_size=100,
            page_table={0: 5, 1: 7, 2: 2},
            tlb_capacity=2,
        )

        first = manager.translate(123)
        second = manager.translate(145)
        manager.translate(201)
        manager.translate(1)  # Evince la page 1, la moins recente du TLB.
        after_eviction = manager.translate(145)

        self.assertEqual((first.page, first.offset, first.frame, first.physical_address), (1, 23, 7, 723))
        self.assertFalse(first.tlb_hit)
        self.assertTrue(second.tlb_hit)
        self.assertFalse(after_eviction.tlb_hit)
        self.assertEqual((manager.tlb_hits, manager.tlb_misses), (1, 4))
        self.assertEqual(manager.tlb_entries, ((0, 5), (1, 7)))
        self.assertAlmostEqual(manager.tlb_hit_ratio, 0.2)
        self.assertAlmostEqual(manager.effective_access_time(10, 100), 190.0)

        missing = manager.translate(350)
        self.assertTrue(missing.page_fault)
        self.assertIsNone(missing.frame)
        self.assertIsNone(missing.physical_address)

    def test_effective_access_time_rejects_non_finite_values_and_overflow(self):
        manager = VirtualMemoryManager(64, {1: 2})
        for tlb_time, memory_time in [
            (float("nan"), 100),
            (10, float("inf")),
            (float("-inf"), 100),
            (10, 1e308),
        ]:
            with self.subTest(tlb_time=tlb_time, memory_time=memory_time):
                with self.assertRaises(VirtualMemoryError):
                    manager.effective_access_time(tlb_time, memory_time)

    def test_demo_shows_a_tlb_hit_and_a_page_fault(self):
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["demo"]), 0)

        display = output.getvalue()
        self.assertIn("adresse physique 139 (TLB hit)", display)
        self.assertIn("page 4, deplacement 4 : DEFAUT DE PAGE", display)
        self.assertIn("8, hits : 1, misses : 7", display)
        self.assertIn("197.50 ns", display)


if __name__ == "__main__":
    unittest.main()
