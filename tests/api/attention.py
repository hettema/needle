"""Reading the head's counts from a served board, in the tests' hands."""


def claim_count(board: dict, claim: str) -> int:
    """How many carry `claim`, or 0 when the head does not list it."""
    for group in ("yours", "broken", "live"):
        for line in board["attention"][group]:
            if line["claim"] == claim:
                return line["count"]
    return 0


def yours(board: dict) -> int:
    return sum(line["count"] for line in board["attention"]["yours"])
