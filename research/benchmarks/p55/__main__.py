"""HybridSign Phase 5.5A research-only CLI."""
import argparse
import json
from pathlib import Path

from . import environment as env


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("install-wheels", help="Install only the verified profile wheels in a research venv")
    setup.add_argument("--wheelhouse", type=Path, required=True)
    modes = ("pilot", "main")
    config = commands.add_parser("config", help="Print the configuration without running a benchmark")
    config.add_argument("--mode", choices=modes, default="pilot")
    config.add_argument("--seed", type=int, default=5501)
    control = commands.add_parser("smoke", help="Run C0-C7 on the generated public fixture")
    run = commands.add_parser("run", help="Create one new paired campaign outside the checkout")
    run.add_argument("--mode", choices=modes, default="pilot")
    run.add_argument("--seed", type=int, default=5501)
    run.add_argument("--accepted-pilot", type=Path)
    export = commands.add_parser("export-bundle", help="Create a small C8 bundle with only public material")
    check = commands.add_parser("verify-bundle", help="Hash and verify an exact C8 bundle with production verification")
    check.add_argument("--bundle", type=Path, required=True)
    check.add_argument("--expect-source", required=True)
    check.add_argument("--expect-producer", choices=env.ENVIRONMENTS, required=True)
    check.add_argument("--expect-run")
    check.add_argument("--expect-attempt")
    for command in (run, control, export, check):
        command.add_argument("--environment", choices=env.ENVIRONMENTS, required=True)
        command.add_argument("--wheelhouse", type=Path, required=True)
        if command != check:
            command.add_argument("--output", type=Path, required=True)
    summary = commands.add_parser("summarize", help="Recalculate descriptive statistics and paired estimators")
    summary.add_argument("--campaign", type=Path, nargs="+", required=True)
    summary.add_argument("--output", type=Path)
    inv = commands.add_parser("check-inventory", help="Verify archived evidence hashes")
    inv.add_argument("--campaign", type=Path, required=True)
    return parser


def main():
    args = build_parser().parse_args()
    if args.command == "install-wheels":
        env.install_wheels(args.wheelhouse)
        return 0

    from . import analysis, controls, protocol

    if args.command == "config":
        profile, target, wheels = env.selected_profile()
        print(json.dumps({**protocol.config(args.mode, args.seed), "platform": target, "profile": profile["id"],
                         "python": profile["python"], "wheels": wheels}, indent=2))
    elif args.command == "run":
        outcome = protocol.run_campaign(args.output, mode=args.mode, seed=args.seed, environment=args.environment,
                                        wheelhouse=args.wheelhouse, pilot_directory=args.accepted_pilot)
        return int(outcome["status"] != "complete")
    elif args.command == "summarize":
        report = analysis.summary(args.campaign)
        if args.output is None:
            print(json.dumps(report, indent=2, allow_nan=False))
        else:
            env.write_json(env.safe_output(args.output, local=False), report)
    elif args.command == "check-inventory":
        print(json.dumps(protocol.check_inventory(args.campaign)))
    else:
        env.runtime_profile(args.environment, args.wheelhouse)
        if args.command == "verify-bundle":
            report = controls.verify_bundle(args.bundle, source_commit=args.expect_source, producer=args.expect_producer,
                                            run_id=args.expect_run, attempt=args.expect_attempt)
            print(json.dumps(report, sort_keys=True))
            return 0
        local = args.environment == "LOCAL-WIN"
        result = env.safe_output(args.output, local=local)
        env.preflight(env.host_state(env.ENVIRONMENTS[args.environment], result.parent))
        if args.command == "smoke":
            result.mkdir()
            report = controls.smoke(result)
            env.write_json(result / "smoke.json", report)
            print(f"{len(report)} controls, {sum(row['passed'] for row in report)} passed")
            return int(not all(row["passed"] for row in report))
        identity = env.execution(args.environment)
        controls.export_bundle(result, environment=args.environment, source_commit=env.git("rev-parse", "HEAD"),
                               run_id=identity["run_id"], attempt=identity["attempt"])
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
