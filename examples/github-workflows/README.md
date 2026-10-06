# Example workflows

These show how a project that *uses* DominoDefBuilder can validate, build and release its Domino modules. They are not run by this repository.

To use one, copy it to `.github/workflows/` in your own module project and adjust it:

- Replace `pip install -e ".[dev]"` with `pip install DominoDefBuilder`, and drop the `pytest` step if you have no tests.
- `build-modules.yml` validates and builds on pushes and pull requests.
- `release-modules.yml` attaches built XML to a GitHub Release. Tags are `modules-v*` (build everything) or `modules/<vendor>/<model>/v<version>` (build one module), deliberately different from this repository's `v*` library tags.

The repository-root `action.yml` is a reusable composite action that wraps the same build.
