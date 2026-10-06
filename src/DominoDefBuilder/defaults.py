from .errors import BuildError
from .xml_writer import node


def formatTempo(tempo):
    return "%.1f" % float(tempo)


def buildEvent(eventSpec):
    if "tag" not in eventSpec:
        raise BuildError("Event is missing tag: " + str(eventSpec))
    attrs = eventSpec.get("attrs", {})
    if not isinstance(attrs, dict):
        raise BuildError("Event attrs must be a mapping: " + str(eventSpec))
    return node(eventSpec["tag"], attrs, (), eventSpec.get("text"))


def buildTrack(trackSpec, endTick):
    events = [buildEvent(eventSpec) for eventSpec in trackSpec.get("events", [])]
    tail = (
        []
        if any(event.tag == "EOT" for event in events)
        else [node("EOT", {"Tick": endTick})]
    )
    attrs = {
        "Name": trackSpec.get("name"),
        "Ch": trackSpec.get("ch"),
        "Mode": trackSpec.get("mode"),
        "Current": 1 if trackSpec.get("current") else None,
    }
    return node("Track", attrs, events + tail)


def buildConductor(spec, endTick):
    if spec.get("conductor"):
        conductor = spec["conductor"]
        attrs = dict(conductor.get("attrs", {}))
        attrs.setdefault("Mode", "Conductor")
        events = [buildEvent(eventSpec) for eventSpec in conductor.get("events", [])]
        if not any(event.tag == "EOT" for event in events):
            events.append(node("EOT", {"Tick": endTick}))
        return node("Track", attrs, events)

    events = []
    if spec.get("tempo", 120.0) is not None:
        events.append(
            node("Tempo", {"Tick": 0, "Tempo": formatTempo(spec.get("tempo", 120.0))})
        )
    if spec.get("mark"):
        events.append(node("Mark", {"Tick": 0, "Name": spec["mark"]}))
    if spec.get("conductorMarks"):
        events.extend(
            node(
                "Mark",
                {
                    "Tick": mark.get("tick"),
                    "Name": mark.get("name"),
                    "Step": mark.get("step"),
                },
            )
            for mark in spec["conductorMarks"]
        )
    if spec.get("timeSignature", "4/4"):
        events.append(
            node(
                "TimeSignature",
                {"TimeSignature": spec.get("timeSignature", "4/4"), "Tick": 0},
            )
        )
    if spec.get("keySignature"):
        events.append(
            node("KeySignature", {"KeySignature": spec["keySignature"], "Tick": 0})
        )
    events.append(node("EOT", {"Tick": endTick}))
    return node("Track", {"Mode": "Conductor"}, events)


def buildDefaultData(spec):
    spec = spec or {}
    endTick = spec.get("endTick", 1920)
    children = []
    for mark in spec.get("marks", []):
        children.append(
            node("Mark", {"Meas": mark.get("meas"), "Name": mark.get("name")})
        )
    trackSpecs = spec.get("tracks") or [{"ch": 1, "current": True}]
    return node(
        "DefaultData",
        {},
        children
        + [buildConductor(spec, endTick)]
        + [buildTrack(trackSpec, endTick) for trackSpec in trackSpecs],
    )


def buildTemplate(templateSpec):
    if not templateSpec.get("name"):
        raise BuildError("Template needs name: " + str(templateSpec))
    events = [buildEvent(eventSpec) for eventSpec in templateSpec.get("events", [])]
    return node(
        "Template", {"ID": templateSpec.get("id"), "Name": templateSpec["name"]}, events
    )


def buildTemplateItem(spec):
    if spec.get("type") != "folder":
        return buildTemplate(spec)
    if not spec.get("name"):
        raise BuildError("Template folder needs name")
    return node(
        "Folder",
        {"Name": spec["name"]},
        [buildTemplateItem(item) for item in spec.get("items", [])],
    )


def buildTemplateList(templateSpecs):
    if not templateSpecs:
        return None
    return node("TemplateList", {}, [buildTemplateItem(spec) for spec in templateSpecs])
