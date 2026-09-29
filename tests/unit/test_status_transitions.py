import itertools

import pytest

from app.models import TERMINAL_STATUSES, WorkflowStatus, can_transition

S = WorkflowStatus


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (S.CREATED, S.RUNNING),
        (S.RUNNING, S.AWAITING_APPROVAL),
        (S.AWAITING_APPROVAL, S.RUNNING),
        (S.AWAITING_APPROVAL, S.REJECTED),
        (S.RUNNING, S.COMPLETED),
        (S.RUNNING, S.FAILED),
    ],
)
def test_legal_transitions(current: S, target: S) -> None:
    assert can_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (S.CREATED, S.COMPLETED),
        (S.CREATED, S.AWAITING_APPROVAL),
        (S.AWAITING_APPROVAL, S.COMPLETED),
    ],
)
def test_illegal_transitions(current: S, target: S) -> None:
    assert not can_transition(current, target)


def test_terminal_states_are_final() -> None:
    for terminal, other in itertools.product(TERMINAL_STATUSES, S):
        if other != terminal:
            assert not can_transition(terminal, other)


def test_same_status_is_allowed_noop() -> None:
    assert all(can_transition(s, s) for s in S)
