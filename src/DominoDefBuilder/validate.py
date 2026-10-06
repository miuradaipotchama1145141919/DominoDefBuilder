from collections import Counter, namedtuple

from .midi import checkData
from .xml_writer import attr, findAll, walk

Issue = namedtuple("Issue", ["level", "message"])

maxCcmId = 1300


def toInt(text):
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def duplicates(values):
    return sorted(value for value, count in Counter(values).items() if count > 1)


def hasErrors(issues):
    return any(issue.level == "error" for issue in issues)


def checkCcmIds(root):
    rawIds = [attr(ccm, "ID") for ccm in findAll(root, "CCM")]
    ids = [toInt(raw) for raw in rawIds]
    invalid = [
        Issue("error", "CCM ID is not an integer: %s" % raw)
        for raw, value in zip(rawIds, ids)
        if value is None
    ]
    outOfRange = [
        Issue("error", "CCM ID out of range 0..%d: %d" % (maxCcmId, value))
        for value in ids
        if value is not None and not 0 <= value <= maxCcmId
    ]
    repeated = [
        Issue("error", "Duplicate CCM ID %s" % value) for value in duplicates(ids)
    ]
    return invalid + outOfRange + repeated


def checkTables(root):
    ids = [toInt(attr(table, "ID")) for table in findAll(root, "Table")]
    known = set(ids)
    negative = [
        Issue("error", "Table ID must be a non-negative integer: %s" % value)
        for value in ids
        if value is None or value < 0
    ]
    repeated = [
        Issue("error", "Duplicate Table ID %s" % value) for value in duplicates(ids)
    ]
    refs = [
        toInt(attr(item, "TableID"))
        for item in walk(root)
        if attr(item, "TableID") is not None
    ]
    missing = [
        Issue("error", "TableID %s does not exist" % value)
        for value in refs
        if value not in known
    ]
    return negative + repeated + missing


def checkLinks(root):
    ccmIds = set(toInt(attr(ccm, "ID")) for ccm in findAll(root, "CCM"))
    folderIds = [
        toInt(attr(folder, "ID"))
        for folder in findAll(root, "Folder")
        if attr(folder, "ID") is not None
    ]
    repeated = [
        Issue("error", "Duplicate Folder ID %s" % value)
        for value in duplicates(folderIds)
    ]
    badCcm = [
        Issue("error", "CCMLink points to missing CCM %s" % attr(link, "ID"))
        for link in findAll(root, "CCMLink")
        if toInt(attr(link, "ID")) not in ccmIds
    ]
    badFolder = [
        Issue("error", "FolderLink points to missing Folder %s" % attr(link, "ID"))
        for link in findAll(root, "FolderLink")
        if toInt(attr(link, "ID")) not in set(folderIds)
    ]
    return repeated + badCcm + badFolder


def checkTemplates(root):
    definitions = [
        toInt(attr(template, "ID"))
        for listing in findAll(root, "TemplateList")
        for template in findAll(listing, "Template")
    ]
    repeated = [
        Issue("error", "Duplicate Template ID %s" % value)
        for value in duplicates(definitions)
    ]
    used = [
        attr(template, "ID")
        for data in findAll(root, "DefaultData")
        for template in findAll(data, "Template")
    ]
    missing = [
        Issue("error", "Template %s is used but not defined" % value)
        for value in used
        if toInt(value) not in set(definitions)
    ]
    return repeated + missing


def checkSelector(value, label):
    if value is None or value == "255":
        return []
    number = toInt(value)
    if number is None or not 0 <= number <= 127:
        return [Issue("error", "%s must be 0..127 or 255: %s" % (label, value))]
    return []


def checkBank(pcLabel, bank):
    issues = checkSelector(attr(bank, "MSB"), pcLabel + " MSB") + checkSelector(
        attr(bank, "LSB"), pcLabel + " LSB"
    )
    badKeys = [
        Issue(
            "error",
            "%s tone key out of range 0..127: %s" % (pcLabel, attr(tone, "Key")),
        )
        for tone in findAll(bank, "Tone")
        if toInt(attr(tone, "Key")) is None or not 0 <= toInt(attr(tone, "Key")) <= 127
    ]
    return issues + badKeys


def checkPc(listName, pc):
    label = "%s %s" % (listName, attr(pc, "Name"))
    number = toInt(attr(pc, "PC"))
    range_ = (
        []
        if number is not None and 1 <= number <= 128
        else [Issue("error", "%s PC must be 1..128: %s" % (label, attr(pc, "PC")))]
    )
    empty = [] if pc.children else [Issue("error", label + " has no Bank")]
    banks = [issue for bank in pc.children for issue in checkBank(label, bank)]
    return range_ + empty + banks


def checkPrograms(root):
    issues = []
    for listName in ("InstrumentList", "DrumSetList"):
        for listing in findAll(root, listName):
            pcs = findAll(listing, "PC")
            issues += [issue for pc in pcs for issue in checkPc(listName, pc)]
            keys = [
                (attr(pc, "PC"), attr(bank, "MSB"), attr(bank, "LSB"))
                for pc in pcs
                for bank in pc.children
            ]
            issues += [
                Issue("warning", "%s repeats PC/MSB/LSB %s" % (listName, key))
                for key in duplicates(keys)
            ]
    return issues


def checkRange(item, label):
    low = toInt(attr(item, "Min", "0"))
    high = toInt(attr(item, "Max", "127"))
    default = toInt(attr(item, "Default"))
    issues = []
    if high is not None and low is not None and low > high:
        issues.append(Issue("error", "%s Min above Max" % label))
    if default is not None and low is not None and default < low:
        issues.append(Issue("error", "%s Default below Min" % label))
    if default is not None and high is not None and default > high:
        issues.append(Issue("error", "%s Default above Max" % label))
    if high is not None:
        issues += [
            Issue("warning", "%s entry %s above Max" % (label, attr(entry, "Value")))
            for entry in findAll(item, "Entry")
            if (toInt(attr(entry, "Value")) or 0) > high
        ]
    return issues


def checkValues(root):
    return [
        issue
        for ccm in findAll(root, "CCM")
        for child in ccm.children
        if child.tag in ("Value", "Gate")
        for issue in checkRange(child, "CCM %s %s" % (attr(ccm, "ID"), child.tag))
    ]


def checkDataText(label, text):
    return [
        Issue(level, "%s: %s" % (label, message))
        for level, message in checkData(text or "")
    ]


def checkAllData(root):
    fromCcm = [
        issue
        for ccm in findAll(root, "CCM")
        for data in findAll(ccm, "Data")
        for issue in checkDataText("CCM %s" % attr(ccm, "ID"), data.text)
    ]
    fromDefault = [
        issue
        for item in findAll(root, "ExclusiveEventDefault")
        for issue in checkDataText(
            "ExclusiveEventDefault", "@SYSEX " + (attr(item, "Data") or "")
        )
    ]
    return fromCcm + fromDefault


def checkEncoding(root):
    texts = [
        text
        for item in walk(root)
        for text in [item.text or ""] + [value for _, value in item.attrs]
    ]
    bad = [text for text in texts if not canEncode(text)]
    return [Issue("error", "Not representable in Shift_JIS: %s" % text) for text in bad]


def canEncode(text):
    try:
        text.encode("shift_jis")
        return True
    except UnicodeEncodeError:
        return False


templateTags = ("Memo", "CC", "PC", "Comment")
trackTags = (
    "Mark",
    "Tempo",
    "TimeSignature",
    "KeySignature",
    "CC",
    "PC",
    "Comment",
    "Template",
    "EOT",
)


def checkEventTags(container, allowed, label):
    return [
        Issue("error", "%s cannot contain %s" % (label, child.tag))
        for child in container.children
        if child.tag not in allowed
    ]


def checkEvents(root):
    ccmIds = set(toInt(attr(ccm, "ID")) for ccm in findAll(root, "CCM"))
    templates = [
        template
        for listing in findAll(root, "TemplateList")
        for template in findAll(listing, "Template")
    ]
    tracks = findAll(root, "Track")
    tagIssues = [
        issue
        for template in templates
        for issue in checkEventTags(
            template, templateTags, "Template " + str(attr(template, "ID"))
        )
    ]
    tagIssues += [
        issue for track in tracks for issue in checkEventTags(track, trackTags, "Track")
    ]
    channels = [
        Issue("error", "Track Ch must be 1..16: %s" % attr(track, "Ch"))
        for track in tracks
        if attr(track, "Ch") is not None
        and not 1 <= (toInt(attr(track, "Ch")) or 0) <= 16
    ]
    containers = templates + tracks
    badRefs = [
        Issue("error", "CC event points to missing CCM %s" % attr(event, "ID"))
        for container in containers
        for event in container.children
        if event.tag == "CC" and toInt(attr(event, "ID")) not in ccmIds
    ]
    defaultIds = [
        attr(item, "ID") for item in findAll(root, "ControlChangeEventDefault")
    ]
    badDefault = [
        Issue("error", "ControlChangeEventDefault points to missing CCM %s" % value)
        for value in defaultIds
        if toInt(value) not in ccmIds
    ]
    return tagIssues + channels + badRefs + badDefault


def validateTree(root):
    checks = (
        checkEvents,
        checkCcmIds,
        checkTables,
        checkLinks,
        checkTemplates,
        checkPrograms,
        checkValues,
        checkAllData,
        checkEncoding,
    )
    return [issue for check in checks for issue in check(root)]
