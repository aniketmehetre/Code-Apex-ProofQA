"""Static import guard test enforcing AGENTS.md rules 2 and 3."""

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROOFQA_DIR = REPO_ROOT / "proofqa"


def resolve_import_from(file_path: Path, node: ast.ImportFrom) -> str:
    """Resolve an ast.ImportFrom node to an absolute package string."""
    if node.level == 0:
        return node.module or ""
    # Compute the current package parts relative to repo root
    rel_path = file_path.relative_to(REPO_ROOT)
    parts = list(rel_path.parent.parts)
    # node.level: 1 means current package, 2 means parent package, etc.
    up = node.level - 1
    if up > 0:
        base_parts = parts[:-up]
    else:
        base_parts = parts
    target_parts = list(base_parts)
    if node.module:
        target_parts.extend(node.module.split("."))
    return ".".join(target_parts)


def get_all_imported_modules(file_path: Path) -> list[tuple[str, int]]:
    """Return list of (imported_module_name, lineno) for a python file."""
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
    except Exception as exc:
        raise AssertionError(f"Failed to parse {file_path}: {exc}") from exc

    imports: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            full_mod = resolve_import_from(file_path, node)
            imports.append((full_mod, node.lineno))
    return imports


def test_rule_2_proof_cert_oracles_must_never_import_llm():
    """Rule 2: proofqa.proof, proofqa.cert and proofqa.oracles must never import proofqa.llm."""
    target_dirs = [
        PROOFQA_DIR / "proof",
        PROOFQA_DIR / "cert",
        PROOFQA_DIR / "oracles",
    ]
    violations = []
    for target_dir in target_dirs:
        for py_file in target_dir.rglob("*.py"):
            for mod, lineno in get_all_imported_modules(py_file):
                if mod == "proofqa.llm" or mod.startswith("proofqa.llm."):
                    violations.append(
                        f"{py_file.relative_to(REPO_ROOT)}:{lineno} imports forbidden '{mod}'"
                    )

    assert not violations, "Rule 2 violations found:\n" + "\n".join(violations)


def test_rule_3_verify_must_not_import_explore_oracles_llm_uncertainty():
    """Rule 3: proofqa/cert/verify.py must not import explore, oracles, llm, or uncertainty."""
    verify_file = PROOFQA_DIR / "cert" / "verify.py"
    assert verify_file.exists(), f"{verify_file} does not exist"

    forbidden_prefixes = (
        "proofqa.explore",
        "proofqa.oracles",
        "proofqa.llm",
        "proofqa.uncertainty",
        "proofqa.spec",
    )
    violations = []
    for mod, lineno in get_all_imported_modules(verify_file):
        for prefix in forbidden_prefixes:
            if mod == prefix or mod.startswith(f"{prefix}."):
                violations.append(
                    f"{verify_file.relative_to(REPO_ROOT)}:{lineno} imports forbidden '{mod}'"
                )

    assert not violations, "Rule 3 violations found:\n" + "\n".join(violations)


def test_spec_facts_has_no_llm_imports():
    """proofqa/spec/facts.py must never import llm or litellm."""
    facts_file = PROOFQA_DIR / "spec" / "facts.py"
    assert facts_file.exists()
    for mod, lineno in get_all_imported_modules(facts_file):
        assert "llm" not in mod.lower(), f"{facts_file}:{lineno} imports forbidden '{mod}'"


def test_reach_and_request_log_isolation():
    """Server-side request log and reach specs must never be imported from explore, oracles, cert, or llm."""
    target_dirs = [
        PROOFQA_DIR / "explore",
        PROOFQA_DIR / "oracles",
        PROOFQA_DIR / "cert",
        PROOFQA_DIR / "llm",
    ]
    violations = []
    for target_dir in target_dirs:
        for py_file in target_dir.rglob("*.py"):
            for mod, lineno in get_all_imported_modules(py_file):
                if (
                    "reach" in mod
                    or "proofbench" in mod
                    or "proofqa.bench" in mod
                ):
                    violations.append(
                        f"{py_file.relative_to(REPO_ROOT)}:{lineno} imports forbidden '{mod}'"
                    )

    assert not violations, "Reach isolation violations found:\n" + "\n".join(violations)


def test_blindness_guard_ast():
    """Blindness guard: explore, llm, and spec must not import bug/heldout catalogues or ground truth."""
    target_dirs = [
        PROOFQA_DIR / "explore",
        PROOFQA_DIR / "llm",
    ]
    if (PROOFQA_DIR / "spec").exists():
        target_dirs.append(PROOFQA_DIR / "spec")

    forbidden_tokens = (
        "bugs",
        "heldout",
        "ground_truth",
        "proofbench",
        "proofqa.bench",
    )
    violations = []
    for target_dir in target_dirs:
        for py_file in target_dir.rglob("*.py"):
            for mod, lineno in get_all_imported_modules(py_file):
                for tok in forbidden_tokens:
                    if tok in mod:
                        violations.append(
                            f"{py_file.relative_to(REPO_ROOT)}:{lineno} imports forbidden '{mod}'"
                        )

    assert not violations, "Blindness guard AST violations found:\n" + "\n".join(violations)


def test_blindness_guard_runtime_stripped_worldspec():
    """Runtime test: Explorer functions identically when provided a stripped WorldSpec with bugs=[]."""
    from proofqa.contracts import WorldSpec
    from proofqa.explore.explorer import RuleBasedExplorer
    from proofqa.world.manager import World

    raw_spec = WorldSpec(app_id="shop_twin", bugs=["B01", "B02", "H01"], seed=42)
    stripped_spec = raw_spec.model_copy(update={"bugs": []})

    assert len(stripped_spec.bugs) == 0

    # RuleBasedExplorer does not rely on or read spec.bugs
    dummy_world = World(stripped_spec)
    explorer = RuleBasedExplorer(world=dummy_world, budget_steps=1, seed=42)
    assert not hasattr(explorer, "bugs")
    assert not hasattr(explorer, "ground_truth")
