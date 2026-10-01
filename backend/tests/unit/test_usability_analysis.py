"""The scoring behind the usability study verdict (WBS 5.4 / NFR2) must not be wrong."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "usability_analysis", BACKEND_ROOT / "scripts" / "usability_analysis.py"
)
assert _spec is not None and _spec.loader is not None
usability = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = usability
_spec.loader.exec_module(usability)

OBS_HEADER = "participant,task,outcome,seconds,critical_errors,seq\n"
SUS_HEADER = "participant," + ",".join(f"q{n}" for n in range(1, 11)) + "\n"
GOOD_SUS = "5,1,5,1,5,1,5,1,5,1"  # the best possible answers: 100
BAD_SUS = "1,5,1,5,1,5,1,5,1,5"  # the worst possible answers: 0


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def _passing_study(tmp_path: Path) -> tuple[Path, Path]:
    obs = OBS_HEADER + "".join(
        f"p{p},T{t},success,60,0,6\n" for p in range(1, 6) for t in range(1, 4)
    )
    sus = SUS_HEADER + "".join(f"p{p},{GOOD_SUS}\n" for p in range(1, 6))
    return _write(tmp_path, "obs.csv", obs), _write(tmp_path, "sus.csv", sus)


def test_sus_score_matches_the_published_extremes_and_midpoint() -> None:
    assert usability.sus_score([5, 1, 5, 1, 5, 1, 5, 1, 5, 1]) == 100.0
    assert usability.sus_score([1, 5, 1, 5, 1, 5, 1, 5, 1, 5]) == 0.0
    # All-neutral answers: every item contributes 2, so 20 * 2.5.
    assert usability.sus_score([3] * 10) == 50.0
    # A worked example: items 1,3,5,7,9 are 4,4,2,5,3 -> 3+3+1+4+2; items 2,4,6,8,10 are
    # 2,1,3,2,2 -> 3+4+2+3+3. Sum 28 * 2.5 = 70.
    assert usability.sus_score([4, 2, 4, 1, 2, 3, 5, 2, 3, 2]) == 70.0


@pytest.mark.parametrize("answers", [[3] * 9, [3] * 11, [3] * 9 + [0], [3] * 9 + [6]])
def test_sus_score_rejects_malformed_answers(answers: list[int]) -> None:
    with pytest.raises(ValueError):
        usability.sus_score(answers)


def test_a_study_that_meets_every_threshold_passes_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    obs, sus = _passing_study(tmp_path)
    assert usability.main(["x", str(obs), str(sus), "--check"]) == 0
    out = capsys.readouterr().out
    assert "NFR2 verdict on this data: MET" in out
    assert "SUS: mean 100.0" in out


def test_a_task_below_the_unaided_target_fails_check(tmp_path: Path) -> None:
    rows = [f"p{p},T1,success,60,0,6\n" for p in range(1, 5)] + ["p5,T1,assisted,200,0,3\n"]
    # 4 of 5 unaided is exactly 80 %, which meets the target...
    obs = _write(tmp_path, "obs.csv", OBS_HEADER + "".join(rows))
    sus = _write(
        tmp_path, "sus.csv", SUS_HEADER + "".join(f"p{p},{GOOD_SUS}\n" for p in range(1, 6))
    )
    assert usability.main(["x", str(obs), str(sus), "--check"]) == 0
    # ...and 3 of 5 does not.
    rows[3] = "p4,T1,failed,300,0,2\n"
    obs.write_text(OBS_HEADER + "".join(rows), encoding="utf-8")
    assert usability.main(["x", str(obs), str(sus), "--check"]) == 1


def test_critical_errors_are_tolerated_once_per_task_but_not_twice(tmp_path: Path) -> None:
    rows = [f"p{p},T1,success,60,{1 if p <= 1 else 0},6\n" for p in range(1, 6)]
    sus = _write(
        tmp_path, "sus.csv", SUS_HEADER + "".join(f"p{p},{GOOD_SUS}\n" for p in range(1, 6))
    )
    obs = _write(tmp_path, "obs.csv", OBS_HEADER + "".join(rows))
    assert usability.main(["x", str(obs), str(sus), "--check"]) == 0
    rows[1] = "p2,T1,success,60,2,6\n"
    obs.write_text(OBS_HEADER + "".join(rows), encoding="utf-8")
    assert usability.main(["x", str(obs), str(sus), "--check"]) == 1


def test_a_below_average_sus_fails_even_when_every_task_succeeds(tmp_path: Path) -> None:
    obs, _ = _passing_study(tmp_path)
    sus = _write(
        tmp_path, "sus.csv", SUS_HEADER + "".join(f"p{p},{BAD_SUS}\n" for p in range(1, 6))
    )
    assert usability.main(["x", str(obs), str(sus), "--check"]) == 1


def test_too_few_participants_cannot_pass(tmp_path: Path) -> None:
    obs = _write(
        tmp_path, "obs.csv", OBS_HEADER + "".join(f"p{p},T1,success,60,0,6\n" for p in (1, 2))
    )
    sus = _write(tmp_path, "sus.csv", SUS_HEADER + "".join(f"p{p},{GOOD_SUS}\n" for p in (1, 2)))
    assert usability.main(["x", str(obs), str(sus), "--check"]) == 1


def test_a_missing_sus_questionnaire_is_reported(tmp_path: Path) -> None:
    obs, _ = _passing_study(tmp_path)
    sus = _write(
        tmp_path, "sus.csv", SUS_HEADER + "".join(f"p{p},{GOOD_SUS}\n" for p in range(1, 5))
    )
    _, criteria = usability.evaluate(usability.load_observations(obs), usability.load_sus(sus))
    sus_criterion = next(c for c in criteria if c[0].startswith("every participant has a SUS"))
    assert sus_criterion[1] is False and "p5" in sus_criterion[2]


def test_without_check_a_failing_study_still_exits_zero(tmp_path: Path) -> None:
    obs, _ = _passing_study(tmp_path)
    sus = _write(
        tmp_path, "sus.csv", SUS_HEADER + "".join(f"p{p},{BAD_SUS}\n" for p in range(1, 6))
    )
    assert usability.main(["x", str(obs), str(sus)]) == 0


@pytest.mark.parametrize(
    "row",
    [
        "p1,T1,done,60,0,6",  # unknown outcome
        "p1,T1,success,abc,0,6",  # seconds not a number
        "p1,T1,success,-1,0,6",  # negative time
        "p1,T1,success,60,-1,6",  # negative critical errors
        "p1,T1,success,60,0,8",  # SEQ out of range
        "p1,T1,success,60,0,0",  # SEQ out of range
        ",T1,success,60,0,6",  # no participant
    ],
)
def test_bad_observations_are_rejected_with_a_line_number(tmp_path: Path, row: str) -> None:
    path = _write(tmp_path, "obs.csv", OBS_HEADER + row + "\n")
    with pytest.raises(ValueError, match="line 2"):
        usability.load_observations(path)


def test_duplicate_rows_and_missing_columns_are_rejected(tmp_path: Path) -> None:
    dup = _write(tmp_path, "dup.csv", OBS_HEADER + "p1,T1,success,60,0,6\np1,T1,success,70,0,6\n")
    with pytest.raises(ValueError, match="duplicate"):
        usability.load_observations(dup)
    short = _write(tmp_path, "short.csv", "participant,task\np1,T1\n")
    with pytest.raises(ValueError, match="missing column"):
        usability.load_observations(short)
    dup_sus = _write(tmp_path, "dup_sus.csv", SUS_HEADER + f"p1,{GOOD_SUS}\np1,{GOOD_SUS}\n")
    with pytest.raises(ValueError, match="duplicate"):
        usability.load_sus(dup_sus)
    bad_sus = _write(tmp_path, "bad_sus.csv", SUS_HEADER + "p1,5,1,5,1,5,1,5,1,5,9\n")
    with pytest.raises(ValueError, match="between 1 and 5"):
        usability.load_sus(bad_sus)


def test_blank_template_rows_are_ignored(tmp_path: Path) -> None:
    path = _write(tmp_path, "obs.csv", OBS_HEADER + ",,,,,\np1,T1,success,60,0,6\n")
    assert len(usability.load_observations(path)) == 1


def test_main_reports_usage_and_unreadable_input(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert usability.main(["x"]) == 2
    assert usability.main(["x", str(tmp_path / "none.csv"), str(tmp_path / "none2.csv")]) == 2
    empty = _write(tmp_path, "empty.csv", OBS_HEADER)
    sus = _write(tmp_path, "sus.csv", SUS_HEADER + f"p1,{GOOD_SUS}\n")
    assert usability.main(["x", str(empty), str(sus)]) == 2
    assert "no data rows" in capsys.readouterr().err
