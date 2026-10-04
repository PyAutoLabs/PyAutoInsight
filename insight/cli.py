"""``pyauto-insight``: the organ's command line (check, board, census, fetch)."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

from insight import ORGAN_ROOT, board, campaigns, ingest, registry
from insight import summary as summary_mod


def _sources(values, instances) -> dict[str, Path]:
    """Parse ``--from`` values: ``<instance>=<path>``, or a bare ``<path>``.

    A bare path is matched to the instance whose repo name is the path's
    basename, or to the only instance when the registry has just one.
    """
    names = {i.instance for i in instances}
    out = {}
    for value in values or []:
        name, sep, path = value.partition("=")
        if sep and name in names:
            out[name] = Path(path).expanduser()
            continue
        path = Path(value).expanduser()
        base = path.resolve().name if path.is_dir() else None
        match = [i.instance for i in instances if i.repo == base]
        if not match and len(instances) == 1:
            match = [instances[0].instance]
        if len(match) != 1:
            raise SystemExit(f"pyauto-insight: cannot tell which instance --from {value} is for")
        out[match[0]] = path
    return out


def _load(args):
    instances = registry.load(args.registry, mind=getattr(args, "mind", None))
    return instances, _sources(getattr(args, "sources", None), instances)


def _ingest_all(args, instances, sources) -> list[ingest.Snapshot]:
    return [
        ingest.ingest(
            inst,
            args.out,
            offline=getattr(args, "offline", False),
            local_path=sources.get(inst.instance),
        )
        for inst in instances
    ]


def _say(s: ingest.Snapshot) -> str:
    key = s.instance.instance
    if s.doc:
        line = (
            f"{key}: {board.integrity(s)}; {len(board.records(s))} records at "
            f"{(s.commit or 'unknown')[:8]}; {board.freshness(s)}; {board.qualification(s)}"
        )
    else:
        line = f"{key}: {board.integrity(s)}"
    if s.failed:
        line += f" — {'; '.join(s.errors)}"
    return line


def cmd_board(args) -> int:
    instances, sources = _load(args)
    views = _ingest_all(args, instances, sources)
    for path in board.write(views, args.out):
        print(f"wrote {path}")
    for s in views:
        print(_say(s), file=sys.stderr if s.failed else sys.stdout)
    return 0


def cmd_fetch(args) -> int:
    instances = registry.load(args.registry, mind=args.mind)
    chosen = [registry.get(instances, args.instance)] if args.instance else instances
    rc = 0
    for inst in chosen:
        s = ingest.ingest(inst, args.out)
        receipt = ingest.read_receipt(args.out, inst.instance) or {}
        print(
            f"{inst.instance}: {receipt.get('outcome')} at "
            f"{(receipt.get('resolved_commit') or 'unresolved')[:12]} "
            f"(receipt {ingest.receipt_path(args.out, inst.instance)})"
        )
        if s.failed:
            print(f"  {'; '.join(s.errors)}", file=sys.stderr)
            rc = 1
    return rc


def cmd_census(args) -> int:
    instances, sources = _load(args)
    for s in _ingest_all(argparse.Namespace(out=args.out, offline=True), instances, sources):
        key = s.instance.instance
        if not s.doc:
            print(f"{key}: no capture ({board.integrity(s)})")
            continue
        doc = s.doc
        print(
            f"{key}: {len(board.records(s))} records · {len(board.comparisons(s))} comparisons · "
            f"{len(doc.get('limitations') or [])} limitations · "
            f"{summary_mod.qualified_records(doc)} qualified · {board.integrity(s)} · "
            f"{(s.commit or 'unknown')[:8]}"
        )
    return 0


def _state_validator():
    """The Brain's cockpit-feed validator (board/_state.py), or None.

    Looked for at $PYAUTO_BRAIN, then beside this organ (flat or grouped
    ``organs/`` layouts both put PyAutoBrain next to PyAutoInsight).
    """
    candidates = []
    if os.environ.get("PYAUTO_BRAIN"):
        candidates.append(Path(os.environ["PYAUTO_BRAIN"]).expanduser())
    candidates.append(ORGAN_ROOT.parent / "PyAutoBrain")
    for root in candidates:
        path = root / "board" / "_state.py"
        if path.is_file():
            spec = importlib.util.spec_from_file_location("_brain_state", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    return None


def _check_state(path: Path) -> list[str]:
    """state.json exists, parses, and (when the Brain is here) meets contract v1."""
    if not path.is_file():
        print("FAIL state: state.json missing — run `pyauto-insight board`")
        return ["state.json missing"]
    try:
        state = json.loads(path.read_text())
    except ValueError as exc:
        print(f"FAIL state: state.json unreadable ({exc})")
        return [f"state.json unreadable: {exc}"]
    validator = _state_validator()
    if validator is None:
        print("skip state: no PyAutoBrain here to validate state.json (set PYAUTO_BRAIN)")
        return []
    errors = validator.validate_state(state)
    if errors:
        print(f"FAIL state: {'; '.join(errors)}")
        return [f"state.json: {e}" for e in errors]
    print(f"ok   state: valid against the Brain contract ({state['status']}, {state['headline']})")
    return []


def cmd_check(args) -> int:
    problems = []
    try:
        campaign_data = campaigns.load()
        campaigns.validate_migration()
    except campaigns.CampaignError as exc:
        print(f"FAIL campaigns: {exc}")
        return 1
    print(
        f"ok   campaigns: {len(campaign_data['campaigns'])} campaigns, {len(campaign_data['tasks'])} tasks"
    )
    try:
        body_map = registry.load_body_map(args.mind)
        print(f"ok   body map: {registry.body_map_path(args.mind)}")
        instances = registry.load(args.registry, body_map=body_map)
    except registry.RegistryError as exc:
        print(f"FAIL registry: {exc}")
        return 1
    print(
        f"ok   registry: {len(instances)} instance(s) "
        f"({', '.join(f'{i.instance}→{i.github}' for i in instances)})"
    )
    sources = _sources(args.sources, instances)
    views = _ingest_all(args, instances, sources)
    mode = "committed receipts + snapshots" if args.offline else "fetched at one resolved commit"
    for s in views:
        key = s.instance.instance
        if s.failed:
            problems.append(f"{key}: {s.outcome}: {'; '.join(s.errors)}")
            print(f"FAIL {key}: {s.outcome}: {'; '.join(s.errors)}")
            continue
        if s.source == "remote":
            receipt = ingest.read_receipt(args.out, key)
            if not receipt or receipt.get("resolved_commit") != s.commit:
                problems.append(f"{key}: receipt does not record the snapshot commit")
                print(f"FAIL {key}: receipt does not record the snapshot commit")
                continue
            # The committed snapshot must still validate under this reader.
            outcome, errors = summary_mod.classify(
                s.doc, (s.instance.schema_name, s.instance.schema_version)
            )
            if outcome != "ok":
                problems.append(f"{key}: snapshot {outcome}: {'; '.join(errors)}")
                print(f"FAIL {key}: snapshot {outcome}: {'; '.join(errors[:5])}")
                continue
        print(
            f"ok   {key}: {s.doc['schema']}@{s.doc['version']} valid, "
            f"{len(board.records(s))} records, {len(board.comparisons(s))} comparisons at "
            f"{(s.commit or 'unknown')[:12]} ({mode if s.source == 'remote' else 'local read'})"
        )
    out = Path(args.out)
    md, page = out / "dashboard.md", out / "dashboard.html"
    if not md.is_file() or not page.is_file():
        problems.append("dashboard.md / dashboard.html missing")
        print("FAIL dashboard: dashboard.md / dashboard.html missing — run `pyauto-insight board`")
    else:
        expected = campaigns.marker(campaign_data)
        digest = board.input_marker(views, campaign_data)
        if digest not in md.read_text() or digest not in page.read_text():
            problems.append("dashboard evidence inputs changed — regenerate board")
        if expected not in md.read_text() or expected not in page.read_text():
            problems.append("campaign dashboard stale — run pyauto-insight board")
            print("FAIL campaigns: dashboard does not match the campaign ledger")
        recorded = board.markers(md.read_text())
        names = {i.instance for i in instances}
        stale = sorted(
            s.instance.instance
            for s in views
            if s.source == "remote"
            and recorded.get(s.instance.instance)
            != {
                "receipt": s.attempt_commit or "none",
                "outcome": s.outcome,
                "shown": s.commit or "none",
            }
        )
        extra = sorted(set(recorded) - names)
        if stale or extra:
            problems.append(f"dashboard stale: {stale + extra}")
            print(
                f"FAIL dashboard: stale for {', '.join(stale + extra)} — run `pyauto-insight board`"
            )
        else:
            print("ok   dashboard: current with every receipt")
    problems += _check_state(out / "state.json")
    print("check: " + ("FAIL" if problems else "OK"))
    return 1 if problems else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="pyauto-insight",
        description="PyAutoInsight: the cross-project inference dashboard organ.",
    )
    parser.add_argument("--registry", default=str(registry.REGISTRY_PATH), help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="cmd", required=True)

    def common(p, reading=True):
        p.add_argument(
            "--mind",
            metavar="PATH",
            help="the PyAutoMind checkout whose repos.yaml resolves each instance's repo "
            "(default: $PYAUTO_MIND, else $PYAUTO_ROOT or beside this organ)",
        )
        p.add_argument("--out", default=str(ORGAN_ROOT), help=argparse.SUPPRESS)
        if reading:
            p.add_argument(
                "--offline",
                action="store_true",
                help="use the committed receipts + snapshots, never the network",
            )
            p.add_argument(
                "--from",
                dest="sources",
                action="append",
                metavar="[INSTANCE=]PATH",
                help="read an instance's summary from this local checkout or file "
                "(labelled as a local read; writes no receipt)",
            )

    p = sub.add_parser(
        "board", help="ingest, then render dashboard.md + dashboard.html + badge.json + state.json"
    )
    common(p)
    p.set_defaults(func=cmd_board)
    p = sub.add_parser(
        "check",
        help="registry + body map valid, every summary ingests and validates, receipt written, "
        "dashboard current, state.json valid",
    )
    common(p)
    p.set_defaults(func=cmd_check)
    p = sub.add_parser(
        "census", help="one line per instance from the committed snapshots (no network)"
    )
    common(p, reading=False)
    p.set_defaults(func=cmd_census, sources=None)
    p = sub.add_parser("fetch", help="ingest and write receipts only (no render)")
    common(p, reading=False)
    p.add_argument("--instance", metavar="K", help="only this instance")
    p.set_defaults(func=cmd_fetch)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except registry.RegistryError as exc:
        print(f"pyauto-insight: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
