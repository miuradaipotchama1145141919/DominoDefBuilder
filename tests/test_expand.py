import pytest

from DominoDefBuilder.errors import BuildError
from DominoDefBuilder.loader import readYaml


def write(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return str(path)


def testLegacyFrom(tmp_path):
    write(tmp_path, "real.yaml", "a: 1\n")
    assert readYaml(write(tmp_path, "top.yaml", "from: real.yaml\n")) == {"a": 1}


def testListSpliceAndGlob(tmp_path):
    write(tmp_path, "parts/b.yaml", "- 2\n- 3\n")
    write(tmp_path, "parts/a.yaml", "- 1\n")
    top = write(tmp_path, "top.yaml", "items:\n  - 0\n  - include: parts/*.yaml\n  - 4\n")
    assert readYaml(top) == {"items": [0, 1, 2, 3, 4]}


def testDictIncludeOverridden(tmp_path):
    write(tmp_path, "base.yaml", "x: 1\ny: 2\n")
    top = write(tmp_path, "top.yaml", "t:\n  include: base.yaml\n  y: 9\n")
    assert readYaml(top) == {"t": {"x": 1, "y": 9}}


def testNestedRelativePaths(tmp_path):
    write(tmp_path, "sub/inner.yaml", "- 7\n")
    write(tmp_path, "sub/mid.yaml", "- include: inner.yaml\n")
    top = write(tmp_path, "top.yaml", "v:\n  - include: sub/mid.yaml\n")
    assert readYaml(top) == {"v": [7]}


def testCircularInclude(tmp_path):
    write(tmp_path, "a.yaml", "- include: b.yaml\n")
    write(tmp_path, "b.yaml", "- include: a.yaml\n")
    with pytest.raises(BuildError):
        readYaml(str(tmp_path / "a.yaml"))


def testMissingInclude(tmp_path):
    with pytest.raises(BuildError):
        readYaml(write(tmp_path, "top.yaml", "- include: nope/*.yaml\n"))


def testForRange(tmp_path):
    top = write(
        tmp_path,
        "top.yaml",
        "programs:\n  - for: n\n    in: {range: [1, 3]}\n"
        "    do: {pc: \"{n}\", name: \"Prog {n:03}\", next: \"{n + 1}\"}\n",
    )
    assert readYaml(top)["programs"] == [
        {"pc": 1, "name": "Prog 001", "next": 2},
        {"pc": 2, "name": "Prog 002", "next": 3},
        {"pc": 3, "name": "Prog 003", "next": 4},
    ]


def testForListOfMappingsAndIndex(tmp_path):
    top = write(
        tmp_path,
        "top.yaml",
        "- for: bank\n  in:\n    - {msb: 0, label: A}\n    - {msb: 1, label: B}\n"
        "  do: {name: \"{label}{index}\", msb: \"{msb}\"}\n",
    )
    assert readYaml(top) == [{"name": "A0", "msb": 0}, {"name": "B1", "msb": 1}]


def testNestedForAndKeySubstitution(tmp_path):
    top = write(
        tmp_path,
        "top.yaml",
        "- for: m\n  in: {range: [1, 2]}\n  do:\n    for: l\n    in: {range: [0, 1]}\n"
        "    do: {\"{m}\": \"{l}\"}\n",
    )
    assert readYaml(top) == [{1: 0}, {1: 1}, {2: 0}, {2: 1}]


def testUnknownPlaceholderKept(tmp_path):
    top = write(tmp_path, "top.yaml", "memo: \"{keep} me\"\n")
    assert readYaml(top) == {"memo": "{keep} me"}


def testIncludeWithParameters(tmp_path):
    write(tmp_path, "tpl.yaml", "name: \"Bank {id}\"\n")
    top = write(
        tmp_path,
        "top.yaml",
        "- include: tpl.yaml\n  with: {id: 5}\n",
    )
    assert readYaml(top) == [{"name": "Bank 5"}]


def testBadFor(tmp_path):
    with pytest.raises(BuildError):
        readYaml(write(tmp_path, "top.yaml", "- for: n\n  in: [1]\n"))
