from .errors import BuildError


def composeSysex(profile, address, payload):
    header = profile.get("header", "F0H")
    footer = profile.get("footer", "F7H")
    inner = " ".join(part for part in (address, payload) if part)
    wrapped = "[ " + inner + " ]" if profile.get("checksum") and inner else inner
    return " ".join(part for part in ("@SYSEX", header, wrapped, footer) if part)


def lookupProfile(sysexSpec, profiles, label):
    name = sysexSpec.get("profile")
    if name is None:
        return sysexSpec
    if name not in profiles:
        raise BuildError("%s: unknown sysex profile %s" % (label, name))
    return profiles[name]


def resolveData(ccmSpec, profiles):
    if "data" in ccmSpec:
        return str(ccmSpec["data"]).strip()
    sysexSpec = ccmSpec.get("sysex")
    if sysexSpec is None:
        return ""
    profile = lookupProfile(
        sysexSpec, profiles, str(ccmSpec.get("name", ccmSpec.get("id")))
    )
    return composeSysex(
        profile, str(sysexSpec.get("address", "")), str(sysexSpec.get("payload", ""))
    )
