"""The public repository carries no other project's content (plan 01b, item 4).

Two halves. The tracked tree carries none of the first real project's card
titles: the titles are held here as fingerprints, not as text, so this file is
not itself an offender, and every line of every tracked file is checked by
sliding a window of each title's word count over it. And the frontend's board
snapshot is generated from the synthetic project by `tools/board_fixture.py`,
so a hand edit that reintroduces real content, or a domain change the
snapshot has not caught up with, fails here.

To fingerprint a title, call `fingerprint()` below with it.
"""

import hashlib
import re
import subprocess
import unicodedata
from pathlib import Path

from tests.ratchets.paths import REPO

FINGERPRINTS: dict[str, int] = {
    "0d051d2cf7afe8cc": 11,
    "f62e98fd41291569": 12,
    "a91f60f330bfb2f0": 9,
    "f9da096cabba1096": 6,
    "a652be4870a6b856": 7,
    "ee1dfb4f96ebbe02": 8,
    "12bd20318f64ac7f": 8,
    "e3eb1fca6743e161": 7,
    "e8c56a715eb18bcf": 8,
    "4e359c1393e12c51": 8,
    "ff7faa6883b72af6": 9,
    "b6a47265e7dcfd28": 7,
    "bf3a7f2cce7933a3": 6,
    "f524c2e00fbc2f10": 9,
    "b23f83023b210a88": 6,
    "6db52b850feb5cc8": 4,
    "ecbd22533dfcc807": 7,
    "551a4ada5f9cdd66": 7,
    "35bbab6476d7bf91": 6,
    "9ea7c111671010c6": 6,
    "27fea0d47fbed8c9": 7,
    "a740ed57388e79c4": 6,
    "031044bc106d5060": 7,
    "abc6e8337f19bf82": 5,
    "a4b54a236484f2db": 7,
    "36d857d7eebd69fc": 10,
    "35d599684feae41b": 7,
    "f8b908701f9293c1": 6,
    "d83dcfbd54c6c8f5": 6,
    "c70ca1a9c908ec43": 7,
    "e92b23be3c2de59a": 4,
    "052aece3d312b771": 5,
    "3aedcbd79845c4c8": 5,
    "7feeff5b76671376": 6,
    "6cf69d8e8118f499": 8,
    "89a8e0446e3d4206": 5,
    "578cfe88f23e4ca0": 8,
    "f08ea6db34c065ac": 9,
    "d38bb8d1c8e6830c": 7,
    "6cdad374e3ef9c6e": 5,
    "916bcb9be31c40a6": 6,
    "9e9468e1e71bbe60": 6,
    "b503fd0a8d07fdd4": 4,
    "9b5c0ec1d07ac40f": 5,
    "008621e2f7d57bef": 5,
    "560cc3fbf0f36426": 5,
    "71bd9ac707c00064": 6,
    "b67408df3dbdf086": 12,
    "945add3adee3ba0f": 13,
    "757a908bc297d609": 7,
    "2fcf046960a7812f": 6,
    "018b4f42b40c92e2": 10,
    "4208ec8ddd844bb9": 9,
    "aa857445487619b5": 7,
    "f711ca2fdfd0ca60": 9,
    "70c36aa44f91308f": 13,
    "5be516bf5d2cd2a1": 5,
    "d1dc77d2d95b5e94": 4,
    "f9ae66e3e6cd048b": 6,
    "66ed081abd82e5ef": 11,
    "0efa0ce7b43c5aac": 7,
    "ab68c3af766c2759": 7,
    "11f13bfb45400b95": 7,
    "71e945ebb8a7ed47": 7,
    "941a54d994c0735c": 8,
    "d5a5522d02aaaab6": 10,
    "cfcbfd7daac71bb1": 6,
    "1e0cc62716e4094a": 11,
    "f0f58e8c38d37b16": 8,
    "6b649808900b0dd0": 6,
    "a0c051e09166726a": 8,
    "34a0adc600962bac": 8,
    "70d6951cace0e227": 10,
    "ff287f5bbc8b64d3": 10,
    "67ecdc03ffca33b2": 8,
    "584f36c27ae7a6aa": 6,
    "91911e193961def2": 6,
    "d6ade12577cac260": 5,
    "4559c1c78e87ca3b": 5,
    "18b34c79ee969def": 5,
    "c7a424421aa49de4": 5,
    "6432676777eaf0e0": 6,
    "94b98d9758369865": 6,
    "73e766d379557ffc": 6,
    "a7bc27aee6277591": 7,
    "43dedb63f2b7e9b2": 5,
    "322ce7aaf7a93748": 7,
    "04a3633e3a1439e8": 4,
    "31fa150678615da3": 6,
    "6fad3634ad4bc10c": 10,
    "607eeaae91bf4ff3": 8,
    "6f0d66524aab3cb1": 6,
    "df51f99f3663e2ca": 9,
    "c9320b24dbcc40d9": 4,
    "8405b7a467a83d84": 6,
    "a2775be2b1dd1ef3": 4,
    "0ad539061ba7e2a1": 4,
    "57445e62de73b807": 6,
    "cf6b242f145c4d45": 5,
    "2c9d6c00e1ed5e0e": 4,
    "3054285490365a95": 6,
    "3af86e996a533cde": 6,
    "cbad2b47e2e3c5ae": 10,
    "36256dc8c19ba468": 6,
    "b5ddf6fc8b98af1a": 9,
    "db27fa6062f28583": 6,
    "e10f3fe889447335": 6,
    "d7743a1eda874c80": 6,
    "6c157bb4cde48222": 7,
    "446e1e24860a1905": 6,
    "500e6e0d13f177d3": 7,
    "641f34d56509db79": 6,
}
"""Fingerprint → word count, for the first real project's 112 card titles of
four words or more, its own board-and-lane vocabulary left out. Made once from
that project's 0.1 card file, which this repository never contains."""

_QUOTES = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'})
_NOT_WORD = re.compile(r"[^a-z0-9' ]+")
_TEXT_SUFFIXES = {".md", ".py", ".ts", ".tsx", ".css", ".html", ".json", ".toml", ".yaml", ".yml"}
_SKIPPED = {"uv.lock", "package-lock.json"}


def words(text: str) -> list[str]:
    plain = unicodedata.normalize("NFKC", text).translate(_QUOTES).lower()
    return _NOT_WORD.sub(" ", plain).split()


def fingerprint(title: str) -> str:
    return hashlib.blake2b(" ".join(words(title)).encode(), digest_size=8).hexdigest()


def _tracked_text_files() -> list[Path]:
    listed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO, capture_output=True, check=True
    ).stdout.decode()
    files = [REPO / name for name in listed.split("\0") if name]
    return [
        f for f in files if f.suffix in _TEXT_SUFFIXES and f.name not in _SKIPPED and f.is_file()
    ]


def _matches(line: str, lengths: set[int]) -> list[str]:
    tokens = words(line)
    found: list[str] = []
    for length in lengths:
        for start in range(len(tokens) - length + 1):
            window = " ".join(tokens[start : start + length])
            digest = hashlib.blake2b(window.encode(), digest_size=8).hexdigest()
            if FINGERPRINTS.get(digest) == length:
                found.append(window)
    return found


def test_no_real_card_title_is_in_the_tracked_tree():
    lengths = set(FINGERPRINTS.values())
    offenders: list[str] = []
    for path in _tracked_text_files():
        if path == Path(__file__):
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for window in _matches(line, lengths):
                offenders.append(f'{path.relative_to(REPO)}:{number}: "{window}"')
    assert not offenders, "a real project's card titles are in the tree:\n" + "\n".join(offenders)


def test_the_ratchet_sees_a_fingerprinted_title():
    title = "Sample title, four words"
    FINGERPRINTS[fingerprint(title)] = 4
    try:
        assert _matches(f"<h3>{title}</h3>", {4}) == ["sample title four words"]
    finally:
        del FINGERPRINTS[fingerprint(title)]


def test_the_frontend_snapshot_is_the_synthetic_project_as_served():
    from tools.board_fixture import FIXTURE, render

    assert FIXTURE.is_file() and FIXTURE.read_text(encoding="utf-8") == render(), (
        "frontend/tests/fixture.json is not what tools/board_fixture.py generates; "
        "run `uv run python tools/board_fixture.py`"
    )
