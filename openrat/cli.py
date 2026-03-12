import argparse
import sys
from .api import run, OpenRatAgent
from .errors import OpenratError


def main(argv=None):
    parser = argparse.ArgumentParser(prog="openrat", description="OpenRat CLI")
    sub = parser.add_subparsers(dest="cmd")

    run_p = sub.add_parser("run", help="Run an experiment file")
    run_p.add_argument("path", help="Path to experiment.py")
    run_p.add_argument("--executor", choices=["docker", "local"], help="Executor to use (docker preferred)")
    run_p.add_argument("--timeout", type=int, help="Execution timeout seconds")

    args = parser.parse_args(argv)

    if args.cmd == "run":
        try:
            agent = OpenRatAgent({"executor": args.executor} if args.executor else None)
            res = agent.run(args.path, timeout=args.timeout)
            print("Result:")
            for k, v in res.items():
                print(f"{k}: {v}")
            return 0
        except OpenratError as e:
            print("Error:", e, file=sys.stderr)
            return 2
        except Exception as e:
            print("Error:", e, file=sys.stderr)
            return 2

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
