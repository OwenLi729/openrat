import argparse
import sys

from openrat import Openrat
from openrat.core.errors import OpenratError


def main(argv=None):
    parser = argparse.ArgumentParser(prog="openrat", description="Openrat CLI")
    sub = parser.add_subparsers(dest="cmd")

    run_p = sub.add_parser("run", help="Run an experiment file")
    run_p.add_argument("path", help="Path to experiment.py")
    run_p.add_argument("--executor", choices=["docker"], help="Executor to use")
    run_p.add_argument("--timeout", type=int, help="Execution timeout seconds")

    args = parser.parse_args(argv)

    if args.cmd == "run":
        try:
            app = Openrat({"executor": args.executor} if args.executor else None)
            res = app.run(args.path, timeout=args.timeout)
            print("Result:")
            for key, value in res.items():
                print(f"{key}: {value}")
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