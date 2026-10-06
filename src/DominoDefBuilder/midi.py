import re

commands = ("@CC", "@PB", "@CP", "@PKP", "@RPN", "@NRPN", "@SYSEX")

dynamicTokens = frozenset(
    [
        "#VL",
        "#VH",
        "#GL",
        "#GH",
        "#CH",
        "#1CH",
        "#2CH",
        "#3CH",
        "#PCH",
        "#1RCH",
        "#2RCH",
        "#4RCH",
        "#VF1",
        "#VF2",
        "#VF3",
        "#VF4",
        "#NONE",
        "#VPGL",
        "#VPGH",
    ]
)

rsctPattern = re.compile(r"^#RSCT(RT|PT)[123]P?$")
tokenPattern = re.compile(r"\[|\]|[^\s\[\]]+")
brackets = ("[", "]")
argCounts = {"@PB": 2, "@CP": 1, "@PKP": 2, "@CC": 2, "@RPN": 4, "@NRPN": 4}


def tokenize(data):
    return tokenPattern.findall(data)


def parseLiteral(token):
    text = token.strip()
    try:
        if len(text) > 1 and text[-1] in "hH":
            return int(text[:-1], 16)
        if text[:2].lower() == "0x":
            return int(text[2:], 16)
        return int(text, 10)
    except ValueError:
        return None


def formatByte(value):
    return "%02XH" % value


def rolandChecksum(values):
    return (128 - sum(values) % 128) % 128


def isDynamicToken(token):
    upper = token.upper()
    return upper in dynamicTokens or bool(rsctPattern.match(upper))


def checkToken(token, limit):
    if token in brackets:
        return None
    if token.upper() == "#PCH":
        return ("warning", "#PCH is port dependent")
    if isDynamicToken(token):
        return None
    value = parseLiteral(token)
    if value is None:
        return ("error", "Unknown token " + token)
    if value < 0 or value > limit:
        return ("error", "Value out of range " + token)
    return None


def checkBrackets(tokens):
    marks = [token for token in tokens if token in brackets]
    if marks == list(brackets) * (len(marks) // 2):
        return []
    return [("error", "Checksum brackets must be balanced [ ... ] pairs")]


def checkSysexFrame(body):
    if len(body) < 2 or parseLiteral(body[0]) != 0xF0 or parseLiteral(body[-1]) != 0xF7:
        return [("error", "SysEx must start with F0H and end with F7H")]
    interior = body[1:-1]
    tooHigh = [
        ("error", "SysEx data byte above 7FH: " + token)
        for token in interior
        if (parseLiteral(token) or 0) > 0x7F
    ]
    return tooHigh + checkBrackets(interior)


def splitCommands(tokens):
    segments = []
    for token in tokens:
        if token.startswith("@") or not segments:
            segments.append([token])
        else:
            segments[-1].append(token)
    return segments


def checkSegment(segment):
    command = segment[0].upper()
    if command not in commands:
        return [("error", "Data must start with one of " + ", ".join(commands))]
    body = segment[1:]
    isSysex = command == "@SYSEX"
    limit = 255 if isSysex else 127
    expected = argCounts.get(command)
    countIssues = (
        [("error", "%s needs %d values" % (command, expected))]
        if expected is not None and len(body) != expected
        else []
    )
    tokenIssues = [
        issue for issue in (checkToken(token, limit) for token in body) if issue
    ]
    strayBrackets = (
        [("error", "Brackets are only valid in @SYSEX")]
        if not isSysex and any(token in brackets for token in body)
        else []
    )
    frameIssues = checkSysexFrame(body) if isSysex else []
    return countIssues + tokenIssues + strayBrackets + frameIssues


def checkData(data):
    return [
        issue
        for segment in splitCommands(tokenize(data))
        for issue in checkSegment(segment)
    ]
