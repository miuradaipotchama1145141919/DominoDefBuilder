import os

from .expand import readExpanded

optionalFiles = ("voices", "drums", "controls", "effects", "defaults")


def readYaml(path):
    return readExpanded(path, (), {}) or {}


def loadModule(moduleDir):
    meta = readYaml(os.path.join(moduleDir, "module.yaml"))
    loaded = {
        name: readYaml(os.path.join(moduleDir, name + ".yaml"))
        for name in optionalFiles
        if os.path.isfile(os.path.join(moduleDir, name + ".yaml"))
    }
    return dict(loaded, meta=meta)


def findModules(modulesDir):
    found = []
    for current, dirNames, fileNames in os.walk(modulesDir):
        dirNames[:] = sorted(name for name in dirNames if not name.startswith("_"))
        if "module.yaml" in fileNames:
            found.append(
                (os.path.relpath(current, modulesDir).replace(os.sep, "/"), current)
            )
    return sorted(found)
