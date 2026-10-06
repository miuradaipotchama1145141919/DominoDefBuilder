from DominoDefBuilder.defaults import buildDefaultData, buildTemplateList
from DominoDefBuilder.xml_writer import attr, findAll


def testDefaultSkeleton():
    root = buildDefaultData(None)
    conductor, track = root.children
    assert attr(conductor, "Mode") == "Conductor"
    assert [child.tag for child in conductor.children] == [
        "Tempo",
        "TimeSignature",
        "EOT",
    ]
    assert attr(conductor.children[0], "Tempo") == "120.0"
    assert attr(track, "Current") == "1"
    assert attr(track, "Ch") == "1"


def testMarkAndEndTick():
    root = buildDefaultData({"mark": "Setup", "endTick": 960})
    conductor = root.children[0]
    assert [child.tag for child in conductor.children] == [
        "Tempo",
        "Mark",
        "TimeSignature",
        "EOT",
    ]
    assert attr(conductor.children[-1], "Tick") == "960"


def testTrackEventsKeepOwnEnd():
    spec = {
        "tracks": [
            {"name": "A", "ch": 2, "events": [{"tag": "EOT", "attrs": {"Tick": 10}}]}
        ]
    }
    track = buildDefaultData(spec).children[1]
    assert len(findAll(track, "EOT")) == 1
    assert attr(track, "Tick") is None


def testTemplateList():
    assert buildTemplateList([]) is None
    listing = buildTemplateList(
        [{"id": 3, "name": "Init", "events": [{"tag": "Memo", "text": "hello"}]}]
    )
    template = listing.children[0]
    assert attr(template, "ID") == "3"
    assert template.children[0].text == "hello"


def testFullConductorAndTopLevelMark():
    root = buildDefaultData(
        {
            "marks": [{"meas": 2, "name": "Start"}],
            "keySignature": "C Maj",
            "conductorMarks": [{"tick": 0, "name": "Setup"}],
            "endTick": 960,
        }
    )
    assert attr(root.children[0], "Meas") == "2"
    conductor = root.children[1]
    assert [child.tag for child in conductor.children] == [
        "Tempo",
        "Mark",
        "TimeSignature",
        "KeySignature",
        "EOT",
    ]
    assert attr(conductor.children[1], "Name") == "Setup"


def testTemplateIdOptional():
    listing = buildTemplateList([{"name": "No ID", "events": []}])
    assert attr(listing.children[0], "ID") is None
