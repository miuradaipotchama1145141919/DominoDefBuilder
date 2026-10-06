import argparse
import hashlib
import json
import os
import sys

from .builder import compileModuleDir
from .errors import BuildError
from .loader import findModules
from .scaffold import scaffoldFiles
from .validate import hasErrors
from .xml_writer import attr, serialize


def selectModules(modulesDir, ids):
    found = findModules(modulesDir)
    if not ids:
        return found
    known = dict(found)
    missing = [moduleId for moduleId in ids if moduleId not in known]
    if missing:
        raise BuildError("Unknown module: " + ", ".join(missing))
    return [(moduleId, known[moduleId]) for moduleId in ids]


def reportIssues(moduleId, issues):
    for issue in issues:
        print("%s: %s: %s" % (issue.level, moduleId, issue.message), file=sys.stderr)


def writeModule(outDir, moduleId, root):
    fileName = moduleId.replace("/", "-") + ".xml"
    data = serialize(root)
    with open(os.path.join(outDir, fileName), "wb") as handle:
        handle.write(data)
    return {
        "id": moduleId,
        "name": attr(root, "Name"),
        "version": attr(root, "FileVersion"),
        "file": fileName,
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def compileAll(selected, version):
    return [
        (moduleId,) + compileModuleDir(path, version) for moduleId, path in selected
    ]


def runList(args):
    for moduleId, _ in findModules(args.modules):
        print(moduleId)
    return 0


def runValidate(args):
    results = compileAll(selectModules(args.modules, args.module), None)
    for moduleId, _, issues in results:
        reportIssues(moduleId, issues)
    return 1 if any(hasErrors(issues) for _, _, issues in results) else 0


def runBuild(args):
    selected = selectModules(args.modules, args.module)
    if args.version and len(selected) != 1:
        raise BuildError("--version needs exactly one module")
    results = compileAll(selected, args.version)
    for moduleId, _, issues in results:
        reportIssues(moduleId, issues)
    if any(hasErrors(issues) for _, _, issues in results):
        return 1
    os.makedirs(args.out, exist_ok=True)
    manifest = [writeModule(args.out, moduleId, root) for moduleId, root, _ in results]
    with open(os.path.join(args.out, "manifest.json"), "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    for entry in manifest:
        print("built " + entry["file"])
    return 0


def runNew(args):
    parts = args.module.split("/")
    if len(parts) != 2 or not all(parts):
        raise BuildError("Use vendor/model")
    target = os.path.join(args.modules, *parts)
    if os.path.exists(target):
        raise BuildError("Already exists: " + target)
    os.makedirs(target)
    for name, content in scaffoldFiles(*parts).items():
        with open(os.path.join(target, name), "w", encoding="utf-8") as handle:
            handle.write(content)
    print("created " + target)
    return 0


def buildParser():
    parser = argparse.ArgumentParser(prog="def")
    parser.add_argument("--modules", default="modules")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list").set_defaults(run=runList)
    validate = commands.add_parser("validate")
    validate.add_argument("module", nargs="*")
    validate.set_defaults(run=runValidate)
    build = commands.add_parser("build")
    build.add_argument("module", nargs="*")
    build.add_argument("--out", default="dist")
    build.add_argument("--version")
    build.set_defaults(run=runBuild)
    new = commands.add_parser("new")
    new.add_argument("module")
    new.set_defaults(run=runNew)
    return parser


def main(argv=None):
    args = buildParser().parse_args(argv)
    try:
        return args.run(args)
    except BuildError as error:
        print("error: " + str(error), file=sys.stderr)
        return 1
