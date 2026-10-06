from DominoDefBuilder.midi import checkData, formatByte, parseLiteral, rolandChecksum
from DominoDefBuilder.sysex import composeSysex, resolveData


def levels(data):
    return [level for level, _ in checkData(data)]


def testRolandChecksum():
    assert rolandChecksum([0x40, 0x00, 0x7F, 0x00]) == 0x41


def testParseLiteral():
    assert parseLiteral("F0H") == 0xF0
    assert parseLiteral("0x1f") == 0x1F
    assert parseLiteral("7") == 7
    assert parseLiteral("#VL") is None


def testFormatByte():
    assert formatByte(10) == "0AH"


def testComposeWithChecksum():
    profile = {"header": "F0H 41H 10H 42H 12H", "checksum": True}
    assert (
        composeSysex(profile, "40H 00H 7FH", "00H")
        == "@SYSEX F0H 41H 10H 42H 12H [ 40H 00H 7FH 00H ] F7H"
    )


def testComposeWithoutChecksum():
    profile = {"header": "F0H 43H 10H 4CH"}
    assert (
        composeSysex(profile, "08H #GL 20H", "#VL")
        == "@SYSEX F0H 43H 10H 4CH 08H #GL 20H #VL F7H"
    )


def testResolveDataPrefersRaw():
    assert resolveData({"data": "@CC 7 #VL"}, {}) == "@CC 7 #VL"
    assert resolveData({"name": "Heading"}, {}) == ""


def testValidData():
    assert levels("@CC 7 #VL") == []
    assert levels("@PB #VH #VL") == []
    assert levels("@SYSEX F0H 43H 10H 4CH 08H #GL 20H #VL F7H") == []
    assert levels("@SYSEX F0H 41H [ 40H 00H ] F7H") == []


def testInvalidData():
    assert levels("7 #VL") == ["error"]
    assert levels("@CC 200 #VL") == ["error"]
    assert "error" in levels("@SYSEX F0H 43H F7")
    assert levels("@SYSEX F0H 90H F7H") == ["error"]
    assert levels("@SYSEX 43H 10H") == ["error"]
    assert "error" in levels("@CC [ 7 ]")
    assert levels("@SYSEX F0H [ 40H F7H") == ["error"]


def testPortWarning():
    assert levels("@SYSEX F0H #PCH F7H") == ["warning"]


def testChainedCommands():
    assert levels("@CC 0 1 @CC 32 2") == []
    assert levels("@NRPN 1AH #GL #VL #NONE") == []


def testArgumentCounts():
    assert levels("@CC 7") == ["error"]
    assert levels("@PB #VH") == ["error"]
    assert levels("@RPN 0 0 #VL") == ["error"]
