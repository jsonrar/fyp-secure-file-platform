"""Score the non-expert usability study (WBS 5.4, requirement NFR2) from its two CSV files.

The study plan (docs/usability/STUDY_PLAN.md) records one row per participant and task in
`observations.csv`, and one row per participant in `sus.csv`. This script turns them into the
numbers the plan commits to in advance, so the verdict is computed from the pre-registered
thresholds rather than argued after the results are known.

    python scripts/usability_analysis.py observations.csv sus.csv [--check]

Without `--check` it prints a report and exits 0. With `--check` it exits 1 when any NFR2
criterion is not met, so the same command can gate a results pull request.

observations.csv columns: participant, task, outcome, seconds, critical_errors, seq
    outcome         success   completed with no hint
                    assisted  completed after a hint
                    failed    the facilitator finished it, or the participant gave up
    seconds         time on task, a non-negative number
    critical_errors count of critical errors the plan defines for that task
    seq             Single Ease Question, 1 (very difficult) to 7 (very easy)
sus.csv columns: participant, q1 ... q10, each 1 (strongly disagree) to 5 (strongly agree)
"""

from __future__ import annotations

import csv
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

OUTCOMES = ("success", "assisted", "failed")
SUS_ITEMS = 10

# Pre-registered thresholds. Change them only in the study plan, before any session is run.
UNAIDED_TARGET = 0.80  # every task: at least 80 % of participants finish with no hint
SUS_TARGET = 68.0  # the long-run average SUS score; below it the interface is below average
MIN_PARTICIPANTS = 5  # fewer than this cannot support a verdict at all
MAX_PARTICIPANTS_WITH_CRITICAL_ERROR = 1  # per task


@dataclass(frozen=True, slots=True)
class Observation:
    participant: str
    task: str
    outcome: str
    seconds: float
    critical_errors: int
    seq: int


def sus_score(answers: list[int]) -> float:
    """Brooke's System Usability Scale: odd items score x-1, even items 5-x, total times 2.5."""
    if len(answers) != SUS_ITEMS:
        raise ValueError(f"SUS needs {SUS_ITEMS} answers, got {len(answers)}")
    if any(not 1 <= answer <= 5 for answer in answers):
        raise ValueError("SUS answers must be between 1 and 5")
    total = sum(
        (answer - 1) if index % 2 == 0 else (5 - answer) for index, answer in enumerate(answers)
    )
    return total * 2.5


def _rows(path: Path, required: list[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [name for name in required if name not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path.name} is missing column(s): {', '.join(missing)}")
        return [row for row in reader if any((value or "").strip() for value in row.values())]


def load_observations(path: Path) -> list[Observation]:
    observations: list[Observation] = []
    seen: set[tuple[str, str]] = set()
    required = ["participant", "task", "outcome", "seconds", "critical_errors", "seq"]
    for line, row in enumerate(_rows(path, required), start=2):
        where = f"{path.name} line {line}"
        participant, task = row["participant"].strip(), row["task"].strip()
        if not participant or not task:
            raise ValueError(f"{where}: participant and task are required")
        if (participant, task) in seen:
            raise ValueError(f"{where}: duplicate row for {participant} / {task}")
        seen.add((participant, task))
        outcome = row["outcome"].strip().lower()
        if outcome not in OUTCOMES:
            raise ValueError(f"{where}: outcome must be one of {', '.join(OUTCOMES)}")
        try:
            seconds = float(row["seconds"])
            critical = int(row["critical_errors"])
            seq = int(row["seq"])
        except ValueError as exc:
            raise ValueError(f"{where}: seconds, critical_errors and seq must be numbers") from exc
        if seconds < 0 or critical < 0:
            raise ValueError(f"{where}: seconds and critical_errors cannot be negative")
        if not 1 <= seq <= 7:
            raise ValueError(f"{where}: seq must be between 1 and 7")
        observations.append(Observation(participant, task, outcome, seconds, critical, seq))
    return observations


def load_sus(path: Path) -> dict[str, float]:
    scores: dict[str, float] = {}
    required = ["participant", *(f"q{n}" for n in range(1, SUS_ITEMS + 1))]
    for line, row in enumerate(_rows(path, required), start=2):
        where = f"{path.name} line {line}"
        participant = row["participant"].strip()
        if not participant:
            raise ValueError(f"{where}: participant is required")
        if participant in scores:
            raise ValueError(f"{where}: duplicate row for {participant}")
        try:
            answers = [int(row[f"q{n}"]) for n in range(1, SUS_ITEMS + 1)]
        except ValueError as exc:
            raise ValueError(f"{where}: every answer must be a whole number") from exc
        try:
            scores[participant] = sus_score(answers)
        except ValueError as exc:
            raise ValueError(f"{where}: {exc}") from exc
    return scores


@dataclass(frozen=True, slots=True)
class TaskSummary:
    task: str
    participants: int
    unaided: float
    assisted: float
    failed: float
    median_seconds: float
    mean_seq: float
    participants_with_critical_error: int


def summarise_tasks(observations: list[Observation]) -> list[TaskSummary]:
    tasks = sorted({o.task for o in observations})
    summaries = []
    for task in tasks:
        rows = [o for o in observations if o.task == task]
        count = len(rows)
        summaries.append(
            TaskSummary(
                task=task,
                participants=count,
                unaided=sum(o.outcome == "success" for o in rows) / count,
                assisted=sum(o.outcome == "assisted" for o in rows) / count,
                failed=sum(o.outcome == "failed" for o in rows) / count,
                median_seconds=statistics.median(o.seconds for o in rows),
                mean_seq=statistics.mean(o.seq for o in rows),
                participants_with_critical_error=sum(o.critical_errors > 0 for o in rows),
            )
        )
    return summaries


def evaluate(
    observations: list[Observation], sus: dict[str, float]
) -> tuple[list[TaskSummary], list[tuple[str, bool, str]]]:
    """Return the per-task summaries and the NFR2 criteria as (name, met, detail)."""
    summaries = summarise_tasks(observations)
    participants = {o.participant for o in observations} | set(sus)
    criteria: list[tuple[str, bool, str]] = []

    criteria.append(
        (
            f"at least {MIN_PARTICIPANTS} participants",
            len(participants) >= MIN_PARTICIPANTS,
            f"{len(participants)} participant(s)",
        )
    )
    missing_sus = sorted({o.participant for o in observations} - set(sus))
    criteria.append(
        (
            "every participant has a SUS questionnaire",
            not missing_sus,
            "complete" if not missing_sus else f"missing: {', '.join(missing_sus)}",
        )
    )
    weak = [s.task for s in summaries if s.unaided < UNAIDED_TARGET]
    criteria.append(
        (
            f"every task completed unaided by at least {UNAIDED_TARGET:.0%}",
            not weak,
            "all tasks met" if not weak else f"below target: {', '.join(weak)}",
        )
    )
    unsafe = [
        s.task
        for s in summaries
        if s.participants_with_critical_error > MAX_PARTICIPANTS_WITH_CRITICAL_ERROR
    ]
    criteria.append(
        (
            f"no task with a critical error for more than {MAX_PARTICIPANTS_WITH_CRITICAL_ERROR}"
            " participant",
            not unsafe,
            "none" if not unsafe else f"exceeded on: {', '.join(unsafe)}",
        )
    )
    mean_sus = statistics.mean(sus.values()) if sus else 0.0
    criteria.append(
        (
            f"mean SUS of at least {SUS_TARGET:g}",
            bool(sus) and mean_sus >= SUS_TARGET,
            f"{mean_sus:.1f}" if sus else "no SUS data",
        )
    )
    return summaries, criteria


def render(
    summaries: list[TaskSummary], criteria: list[tuple[str, bool, str]], sus: dict[str, float]
) -> str:
    lines = [
        "| Task | n | Unaided | Assisted | Failed | Median s | Mean SEQ | With critical error |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for s in summaries:
        lines.append(
            f"| {s.task} | {s.participants} | {s.unaided:.0%} | {s.assisted:.0%} | {s.failed:.0%} "
            f"| {s.median_seconds:g} | {s.mean_seq:.1f} | {s.participants_with_critical_error} |"
        )
    lines.append("")
    if sus:
        values = list(sus.values())
        lines.append(
            f"SUS: mean {statistics.mean(values):.1f}, median {statistics.median(values):g}, "
            f"range {min(values):g}-{max(values):g} (n={len(values)})"
        )
        lines.append("")
    lines.append("NFR2 criteria:")
    for name, met, detail in criteria:
        lines.append(f"- [{'x' if met else ' '}] {name} ({detail})")
    verdict = "MET" if all(met for _, met, _ in criteria) else "NOT MET"
    lines.append("")
    lines.append(f"NFR2 verdict on this data: {verdict}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if a != "--check"]
    check = "--check" in argv[1:]
    if len(args) != 2:
        print(
            "usage: usability_analysis.py <observations.csv> <sus.csv> [--check]", file=sys.stderr
        )
        return 2
    try:
        observations = load_observations(Path(args[0]))
        sus = load_sus(Path(args[1]))
    except (OSError, ValueError) as exc:
        print(f"usability_analysis: {exc}", file=sys.stderr)
        return 2
    if not observations:
        print("usability_analysis: observations.csv has no data rows", file=sys.stderr)
        return 2

    summaries, criteria = evaluate(observations, sus)
    print(render(summaries, criteria, sus))
    if check and not all(met for _, met, _ in criteria):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
