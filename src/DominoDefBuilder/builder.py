from .defaults import buildDefaultData, buildTemplateList
from .errors import BuildError
from .loader import loadModule
from .sysex import resolveData
from .validate import validateTree
from .xml_writer import node


def require(spec, key, label):
    if key not in spec or spec[key] in (None, ""):
        raise BuildError("%s: missing %s" % (label, key))
    return spec[key]


# Instruments and drums
def normalizeTones(tones):
    if isinstance(tones, dict):
        return [{"key": int(key), "name": name} for key, name in sorted(tones.items())]
    return list(tones or [])


def buildTone(toneSpec):
    return node(
        "Tone",
        {
            "Name": require(toneSpec, "name", "tone"),
            "Key": require(toneSpec, "key", "tone"),
        },
    )


def resolveTones(bankSpec, toneSets):
    setName = bankSpec.get("toneSet")
    if setName is None:
        return bankSpec.get("tones")
    if setName not in toneSets:
        raise BuildError("Unknown toneSet " + str(setName))
    return toneSets[setName]


def buildBank(bankSpec, fallbackName, toneSets):
    attrs = {
        "Name": bankSpec.get("name", fallbackName),
        "MSB": bankSpec.get("msb"),
        "LSB": bankSpec.get("lsb"),
    }
    return node(
        "Bank",
        attrs,
        [
            buildTone(toneSpec)
            for toneSpec in normalizeTones(resolveTones(bankSpec, toneSets))
        ],
    )


def buildPc(programSpec, toneSets):
    name = require(programSpec, "name", "program")
    banks = programSpec.get("banks") or [{}]
    return node(
        "PC",
        {"Name": name, "PC": require(programSpec, "pc", name)},
        [buildBank(bankSpec, name, toneSets) for bankSpec in banks],
    )


def expandPrograms(mapSpec):
    names = mapSpec.get("names") or []
    start = mapSpec.get("start", 1)
    bank = mapSpec.get("bank", {})
    generated = [
        {"pc": start + index, "name": name, "banks": [dict(bank, name=name)]}
        for index, name in enumerate(names)
    ]
    return generated + list(mapSpec.get("programs", []))


def buildMap(mapSpec, toneSets):
    return node(
        "Map",
        {"Name": require(mapSpec, "name", "map")},
        [buildPc(programSpec, toneSets) for programSpec in expandPrograms(mapSpec)],
    )


def buildProgramList(tag, section):
    toneSets = section.get("toneSets", {})
    return node(
        tag, {}, [buildMap(mapSpec, toneSets) for mapSpec in section.get("maps", [])]
    )


# Controls
def normalizeEntries(entries):
    if isinstance(entries, dict):
        pairs = [(label, value) for value, label in entries.items()]
    else:
        pairs = [(entry["label"], entry["value"]) for entry in entries or []]
    return [(checkLabel(label), value) for label, value in pairs]


def checkLabel(label):
    if isinstance(label, bool):
        raise BuildError("Entry label parsed as a boolean, quote it in YAML")
    return str(label)


def buildEntry(label, value):
    return node("Entry", {"Label": label, "Value": value})


def buildTable(tableSpec):
    return node(
        "Table",
        {"ID": require(tableSpec, "id", "table")},
        [
            buildEntry(label, value)
            for label, value in normalizeEntries(tableSpec.get("entries"))
        ],
    )


def buildValue(tag, spec):
    if spec is None:
        return None
    attrs = {
        "Name": spec.get("name"),
        "Type": spec.get("type"),
        "Default": spec.get("default"),
        "Min": spec.get("min"),
        "Max": spec.get("max"),
        "Offset": spec.get("offset"),
        "TableID": spec.get("tableId"),
    }
    return node(
        tag,
        attrs,
        [
            buildEntry(label, value)
            for label, value in normalizeEntries(spec.get("entries"))
        ],
    )


def buildCcm(spec, profiles):
    label = str(spec.get("name", spec.get("id")))
    attrs = {
        "ID": require(spec, "id", label),
        "Name": require(spec, "name", label),
        "Sync": spec.get("sync"),
        "MuteSync": 1 if spec.get("muteSync") else None,
        "Color": spec.get("color"),
    }
    memo = [node("Memo", {}, (), spec["memo"])] if spec.get("memo") else []
    head = [
        buildValue("Value", spec.get("value")),
        buildValue("Gate", spec.get("gate")),
    ]
    return node(
        "CCM", attrs, head + memo + [node("Data", {}, (), resolveData(spec, profiles))]
    )


def buildLink(tag, spec):
    name = require(spec, "name", tag) if tag == "FolderLink" else None
    attrs = {
        "ID": require(spec, "id", tag),
        "Name": name,
        "Value": spec.get("value"),
        "Gate": spec.get("gate"),
    }
    return node(tag, attrs)


def buildFolder(spec, profiles):
    attrs = {"Name": require(spec, "name", "folder"), "ID": spec.get("id")}
    return node(
        "Folder", attrs, [buildItem(item, profiles) for item in spec.get("items", [])]
    )


def buildItem(spec, profiles):
    kind = spec.get("type")
    if kind == "folder":
        return buildFolder(spec, profiles)
    if kind == "ccm":
        return buildCcm(spec, profiles)
    if kind == "table":
        return buildTable(spec)
    if kind == "ccmLink":
        return buildLink("CCMLink", spec)
    if kind == "folderLink":
        return buildLink("FolderLink", spec)
    raise BuildError("Unknown item type %s in %s" % (kind, spec))


# Module
def optionNodes(meta):
    return [
        (
            node("ControlChangeEventDefault", {"ID": meta["defaultCcmId"]})
            if "defaultCcmId" in meta
            else None
        ),
        (
            node("ExclusiveEventDefault", {"Data": meta["exclusiveDefault"]})
            if "exclusiveDefault" in meta
            else None
        ),
        (
            node("RhythmTrackDefault", {"Gate": meta["rhythmGate"]})
            if "rhythmGate" in meta
            else None
        ),
        (
            node(
                "ProgramChangeEventPropertyDlg",
                {"AutoPreviewDelay": meta["previewDelay"]},
            )
            if "previewDelay" in meta
            else None
        ),
    ]


def collectControls(spec):
    sections = [spec.get("controls") or {}, spec.get("effects") or {}]
    tables = [table for section in sections for table in section.get("tables", [])]
    items = [item for section in sections for item in section.get("items", [])]
    return tables, items


def buildControlList(spec, profiles):
    tables, items = collectControls(spec)
    if not tables and not items:
        return None
    return node(
        "ControlChangeMacroList",
        {},
        [buildTable(table) for table in tables]
        + [buildItem(item, profiles) for item in items],
    )


def buildModule(spec):
    meta = spec["meta"]
    attrs = {
        "Name": require(meta, "name", "module"),
        "Folder": meta.get("folder"),
        "Priority": meta.get("priority", 100),
        "FileCreator": meta.get("creator"),
        "FileVersion": meta.get("version"),
        "WebSite": meta.get("website"),
    }
    children = optionNodes(meta) + [
        (
            buildProgramList("InstrumentList", spec["voices"])
            if "voices" in spec
            else None
        ),
        buildProgramList("DrumSetList", spec["drums"]) if "drums" in spec else None,
        buildControlList(spec, meta.get("profiles", {})),
        buildTemplateList((spec.get("defaults") or {}).get("templates")),
        buildDefaultData(spec.get("defaults")),
    ]
    return node("ModuleData", attrs, children)


def withVersion(spec, version):
    if version is None:
        return spec
    return dict(spec, meta=dict(spec["meta"], version=version))


def compileModuleDir(moduleDir, version=None):
    root = buildModule(withVersion(loadModule(moduleDir), version))
    return root, validateTree(root)
