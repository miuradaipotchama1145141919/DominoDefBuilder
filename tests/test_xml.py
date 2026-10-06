import os
import xml.etree.ElementTree as ET

import pytest

from DominoDefBuilder.builder import compileModuleDir
from DominoDefBuilder.cli import main
from DominoDefBuilder.errors import BuildError
from DominoDefBuilder.loader import findModules
from DominoDefBuilder.validate import hasErrors
from DominoDefBuilder.xml_writer import attr, findAll, node, serialize

here = os.path.dirname(__file__)
fixtureRoot = os.path.join(here, "fixtures", "modules")
repoModules = os.path.join(here, "..", "examples", "modules")


def buildFixture():
    root, issues = compileModuleDir(os.path.join(fixtureRoot, "test", "minimal"))
    return root, issues


def testFixtureHasNoIssues():
    _, issues = buildFixture()
    assert issues == []


def testSerializedHeaderAndParse():
    root, _ = buildFixture()
    data = serialize(root)
    assert data.startswith(b'<?xml version="1.0" encoding="Shift_JIS"?>')
    parsed = ET.fromstring(data.decode("shift_jis").split("?>", 1)[1])
    assert parsed.tag == "ModuleData"
    assert parsed.get("Priority") == "100"
    assert [child.tag for child in parsed][:4] == [
        "ControlChangeEventDefault",
        "ExclusiveEventDefault",
        "RhythmTrackDefault",
        "InstrumentList",
    ]


def testInstrumentExpansion():
    root, _ = buildFixture()
    pcs = findAll(findAll(root, "InstrumentList")[0], "PC")
    assert [attr(pc, "PC") for pc in pcs] == ["1", "2", "3"]
    assert len(pcs[2].children) == 2
    assert attr(pcs[0].children[0], "MSB") is None


def testDrumToneSet():
    root, _ = buildFixture()
    tones = findAll(findAll(root, "DrumSetList")[0], "Tone")
    assert [(attr(tone, "Key"), attr(tone, "Name")) for tone in tones] == [
        ("36", "Kick"),
        ("38", "Snare"),
    ]


def testControlsAndLinks():
    root, _ = buildFixture()
    ccm = findAll(root, "CCM")[0]
    assert attr(ccm, "Sync") == "Last"
    assert findAll(root, "CCMLink")[0].attrs == (("ID", "7"), ("Value", "90"))
    reset = [item for item in findAll(root, "CCM") if attr(item, "ID") == "200"][0]
    assert (
        findAll(reset, "Data")[0].text
        == "@SYSEX F0H 41H 10H 42H 12H [ 40H 00H 7FH 00H ] F7H"
    )


def testVersionOverride():
    root, _ = compileModuleDir(os.path.join(fixtureRoot, "test", "minimal"), "2.50")
    assert attr(root, "FileVersion") == "2.50"


def testUnencodableTextRaises():
    with pytest.raises(BuildError):
        serialize(node("ModuleData", {"Name": "\U0001f3b9"}))


def testRepoModulesAreValid():
    found = findModules(repoModules)
    assert [moduleId for moduleId, _ in found] == ["example/gm2"]
    for moduleId, path in found:
        _, issues = compileModuleDir(path)
        assert not hasErrors(issues), moduleId


def testGmContent():
    root, _ = compileModuleDir(os.path.join(repoModules, "example", "gm2"))
    instrumentList = findAll(root, "InstrumentList")[0]
    pcs = findAll(instrumentList.children[0], "PC")
    assert [attr(pc, "PC") for pc in pcs] == [str(number) for number in range(1, 129)]
    assert attr(pcs[0], "Name") == "Acoustic Grand Piano"
    assert attr(pcs[127], "Name") == "Gunshot"
    tones = findAll(findAll(root, "DrumSetList")[0], "Tone")
    assert len(tones) == 9 * 61


def testSharedSourceViaFrom():
    gm, _ = compileModuleDir(os.path.join(repoModules, "example", "gm2"))
    gs, _ = compileModuleDir(os.path.join(repoModules, "example", "gm2"))
    assert findAll(gm, "InstrumentList") == findAll(gs, "InstrumentList")


def testCliBuild(tmp_path):
    out = tmp_path / "dist"
    code = main(
        ["--modules", fixtureRoot, "build", "--out", str(out), "--version", "3.00"]
    )
    assert code == 0
    assert (out / "test-minimal.xml").exists()
    assert "3.00" in (out / "manifest.json").read_text()


def testCliNewThenBuild(tmp_path):
    modules = tmp_path / "modules"
    assert main(["--modules", str(modules), "new", "acme/box1"]) == 0
    assert main(["--modules", str(modules), "validate"]) == 0
    assert main(["--modules", str(modules), "new", "acme/box1"]) == 1


def testCliUnknownModule(tmp_path):
    assert (
        main(["--modules", fixtureRoot, "build", "nope/none", "--out", str(tmp_path)])
        == 1
    )


def testMemoBeforeData():
    root, _ = compileModuleDir(os.path.join(repoModules, "example", "gm2"))
    pan = [item for item in findAll(root, "CCM") if attr(item, "ID") == "10"][0]
    assert [child.tag for child in pan.children] == ["Value", "Memo", "Data"]


def testExampleUsesTablesLinksAndCommands():
    root, issues = compileModuleDir(os.path.join(repoModules, "example", "gm2"))
    assert not hasErrors(issues)
    assert len(findAll(root, "Table")) >= 3
    assert len(findAll(root, "CCMLink")) >= 2
    assert len(findAll(root, "FolderLink")) >= 2
    ids = {attr(item, "ID") for item in findAll(root, "CCM")}
    assert {"130", "131", "132", "133", "134", "200", "201", "203"} <= ids
    data = " ".join(attr(item, "Data", "") for item in findAll(root, "CCM"))
    assert "@NRPN" not in data
    assert "@CC 94" not in data
    assert "Delay Effect" not in " ".join(
        attr(item, "Name", "") for item in findAll(root, "Folder")
    )


def testExampleDefaultDataIncludesSystemAndDrumKeyBasedControllers():
    root, issues = compileModuleDir(os.path.join(repoModules, "example", "gm2"))
    assert not hasErrors(issues)
    tracks = findAll(root, "Track")
    names = [attr(track, "Name") for track in tracks]
    assert "System Setup" in names
    assert "Drum Key-Based Controllers" in names
    drum = [
        track for track in tracks if attr(track, "Name") == "Drum Key-Based Controllers"
    ][0]
    assert attr(drum, "Ch") == "10"
    assert attr(drum, "Mode") == "Rhythm"
    assert len(findAll(drum, "CC")) == 4


def testColorAttributesUseDominoHexFormat():
    from DominoDefBuilder.xml_writer import node

    assert dict(node("CCM", {"Color": "C000C0"}).attrs)["Color"] == "#C000C0"
    assert dict(node("CCM", {"Color": "#0080e0"}).attrs)["Color"] == "#0080E0"


def testInvalidColorRaisesBuildError():
    from DominoDefBuilder.xml_writer import node

    with pytest.raises(BuildError, match="six-digit RGB"):
        node("CCM", {"Color": "blue"})
