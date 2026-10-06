import ast
import glob
import operator
import os
import re

import yaml

from .errors import BuildError

maxDepth = 16
placeholder = re.compile(r"\{([^{}]+)\}")
binaryOperators = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}


# Expressions
def evalNode(tree, scope):
    if isinstance(tree, ast.Constant) and isinstance(tree.value, (int, str)):
        return tree.value
    if isinstance(tree, ast.Name):
        return scope[tree.id]
    if isinstance(tree, ast.UnaryOp) and isinstance(tree.op, ast.USub):
        return -evalNode(tree.operand, scope)
    if isinstance(tree, ast.BinOp) and type(tree.op) in binaryOperators:
        return binaryOperators[type(tree.op)](
            evalNode(tree.left, scope), evalNode(tree.right, scope)
        )
    raise KeyError(type(tree).__name__)


def evalPlaceholder(body, scope):
    expression, _, spec = body.partition(":")
    try:
        return evalNode(ast.parse(expression.strip(), mode="eval").body, scope), spec
    except (KeyError, SyntaxError):
        return None


def formatValue(value, spec, text):
    try:
        return format(value, spec)
    except (ValueError, TypeError):
        raise BuildError("Bad format in " + text)


def fillString(text, scope):
    whole = placeholder.fullmatch(text)
    found = evalPlaceholder(whole.group(1), scope) if whole else None
    if found and not found[1]:
        return found[0]

    def replace(match):
        result = evalPlaceholder(match.group(1), scope)
        if result is None:
            return match.group(0)
        return formatValue(result[0], result[1], text)

    return placeholder.sub(replace, text)


def fillText(value, scope):
    return fillString(value, scope) if scope and isinstance(value, str) else value


# Files
def readExpanded(path, stack, scope):
    realPath = os.path.realpath(path)
    if realPath in stack:
        raise BuildError("Circular include at " + path)
    if len(stack) >= maxDepth:
        raise BuildError("Includes nested too deeply at " + path)
    if not os.path.isfile(path):
        raise BuildError("File not found: " + path)
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return expandValue(data, (os.path.dirname(path), stack + (realPath,)), scope)


def resolvePaths(target, baseDir, scope):
    if isinstance(target, list):
        return [path for item in target for path in resolvePaths(item, baseDir, scope)]
    pattern = os.path.normpath(os.path.join(baseDir, str(fillText(target, scope))))
    if not glob.has_magic(pattern):
        return [pattern]
    paths = sorted(glob.glob(pattern, recursive=True))
    if not paths:
        raise BuildError("No files match " + pattern)
    return paths


def loadIncludes(spec, ctx, scope):
    baseDir, stack = ctx
    inner = dict(scope, **(expandValue(spec.get("with") or {}, ctx, scope)))
    return [
        readExpanded(path, stack, inner)
        for path in resolvePaths(spec["include"], baseDir, scope)
    ]


def combine(values):
    present = [value for value in values if value is not None]
    if all(isinstance(value, list) for value in present):
        return [item for value in present for item in value]
    if all(isinstance(value, dict) for value in present):
        return {key: item for value in present for key, item in value.items()}
    raise BuildError("Included files must all be lists or all be mappings")


# Directives
def isSplice(item):
    return "include" in item and not set(item) - {"include", "with"}


def rangeItems(spec):
    if isinstance(spec, list):
        return spec
    if isinstance(spec, dict) and list(spec) == ["range"]:
        bounds = spec["range"]
        if not isinstance(bounds, list) or len(bounds) not in (2, 3):
            raise BuildError("range needs [start, stop] or [start, stop, step]")
        step = bounds[2] if len(bounds) == 3 else 1
        return list(range(bounds[0], bounds[1] + (1 if step > 0 else -1), step))
    raise BuildError("for needs in: as a list or a range")


def expandFor(spec, ctx, scope):
    if not isinstance(spec.get("for"), str) or "do" not in spec:
        raise BuildError("for needs a variable name and do")
    extra = set(spec) - {"for", "in", "do"}
    if extra:
        raise BuildError("Unknown for keys: " + ", ".join(sorted(map(str, extra))))
    items = rangeItems(expandValue(spec.get("in"), ctx, scope))
    built = []
    for index, item in enumerate(items):
        fields = item if isinstance(item, dict) else {}
        inner = dict(scope, **fields)
        inner.update({spec["for"]: item, "index": index})
        result = expandValue(spec["do"], ctx, inner)
        built.extend(result if isinstance(result, list) else [result])
    return built


# Values
def spliceItems(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def expandList(items, ctx, scope):
    built = []
    for item in items:
        if isinstance(item, dict) and isSplice(item):
            for value in loadIncludes(item, ctx, scope):
                built.extend(spliceItems(value))
        elif isinstance(item, dict) and "for" in item:
            built.extend(expandFor(item, ctx, scope))
        else:
            built.append(expandValue(item, ctx, scope))
    return built


def expandDict(spec, ctx, scope):
    if "for" in spec:
        return expandFor(spec, ctx, scope)

    isInclude = "include" in spec
    isLegacy = list(spec) == ["from"]
    if not isInclude and not isLegacy:
        return {
            fillText(key, scope): expandValue(value, ctx, scope)
            for key, value in spec.items()
        }
    target = spec if isInclude else {"include": spec["from"]}
    skipped = ("include", "with") if isInclude else ("from",)
    base = combine(loadIncludes(target, ctx, scope))
    rest = {
        fillText(key, scope): expandValue(value, ctx, scope)
        for key, value in spec.items()
        if key not in skipped
    }
    if not rest:
        return base
    if not isinstance(base, dict):
        raise BuildError("include with sibling keys needs mapping files")
    return dict(base, **rest)


def expandValue(value, ctx, scope):
    if isinstance(value, list):
        return expandList(value, ctx, scope)
    if isinstance(value, dict):
        return expandDict(value, ctx, scope)
    return fillText(value, scope)
