from DominoDefBuilder.validate import hasErrors, validateTree
from DominoDefBuilder.xml_writer import node


def wrap(*children):
    return node("ModuleData", {"Name": "T"}, children)


def ccm(ccmId, data="@CC 7 #VL", children=()):
    return node(
        "CCM", {"ID": ccmId, "Name": "x"}, list(children) + [node("Data", {}, (), data)]
    )


def messages(root):
    return [issue.message for issue in validateTree(root)]


def testDuplicateAndRangeIds():
    root = wrap(node("ControlChangeMacroList", {}, [ccm(1), ccm(1), ccm(1301)]))
    found = messages(root)
    assert any("Duplicate CCM ID" in text for text in found)
    assert any("out of range" in text for text in found)


def testMissingLinkTargets():
    root = wrap(
        node(
            "ControlChangeMacroList",
            {},
            [ccm(1), node("CCMLink", {"ID": 9}), node("FolderLink", {"ID": 4})],
        )
    )
    found = messages(root)
    assert any("CCMLink" in text for text in found)
    assert any("FolderLink" in text for text in found)


def testMissingTable():
    value = node("Value", {"TableID": 5})
    root = wrap(node("ControlChangeMacroList", {}, [ccm(1, children=[value])]))
    assert any("TableID 5" in text for text in messages(root))


def testValueRange():
    value = node("Value", {"Min": 10, "Max": 5, "Default": 20})
    root = wrap(node("ControlChangeMacroList", {}, [ccm(1, children=[value])]))
    assert hasErrors(validateTree(root))


def testProgramRules():
    bad = node("PC", {"Name": "a", "PC": 129}, [])
    banked = node(
        "PC", {"Name": "b", "PC": 1}, [node("Bank", {"Name": "b", "MSB": 128})]
    )
    root = wrap(node("InstrumentList", {}, [node("Map", {"Name": "m"}, [bad, banked])]))
    found = messages(root)
    assert any("PC must be 1..128" in text for text in found)
    assert any("has no Bank" in text for text in found)
    assert any("MSB" in text for text in found)


def testToneKey():
    bank = node("Bank", {"Name": "k"}, [node("Tone", {"Name": "t", "Key": 200})])
    root = wrap(
        node(
            "DrumSetList",
            {},
            [node("Map", {"Name": "m"}, [node("PC", {"Name": "k", "PC": 1}, [bank])])],
        )
    )
    assert any("tone key" in text for text in messages(root))


def testTemplateReference():
    track = node("Track", {}, [node("Template", {"ID": 3, "Tick": 0})])
    root = wrap(node("DefaultData", {}, [track]))
    assert any("Template 3" in text for text in messages(root))


def testBadDataReported():
    root = wrap(node("ControlChangeMacroList", {}, [ccm(1, data="@SYSEX F0H 90H F7H")]))
    assert hasErrors(validateTree(root))


def testTemplateTagsAndRefs():
    template = node(
        "Template", {"ID": 0, "Name": "t"}, [node("Bank", {}), node("CC", {"ID": 99})]
    )
    root = wrap(node("TemplateList", {}, [template]))
    found = messages(root)
    assert any("cannot contain Bank" in text for text in found)
    assert any("missing CCM 99" in text for text in found)


def testTrackChannelAndDefaultCcm():
    root = wrap(
        node("ControlChangeEventDefault", {"ID": 5}),
        node("DefaultData", {}, [node("Track", {"Ch": 17})]),
    )
    found = messages(root)
    assert any("Ch must be 1..16" in text for text in found)
    assert any("ControlChangeEventDefault" in text for text in found)


def testImplicitMaxDefault():
    root = wrap(
        node(
            "ControlChangeMacroList",
            {},
            [ccm(1, children=[node("Value", {"Default": 200})])],
        )
    )
    assert hasErrors(validateTree(root))


def testTemplateFolderAccepted():
    template = node("Template", {"ID": 0, "Name": "t"}, [node("Memo", {}, (), "x")])
    root = wrap(
        node("TemplateList", {}, [node("Folder", {"Name": "f"}, [template])]),
        node("DefaultData", {}, [node("Track", {}, [node("Template", {"ID": 0})])]),
    )
    assert validateTree(root) == []
