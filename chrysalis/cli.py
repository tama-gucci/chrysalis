"""Bounded JSON CLI. Approval and setup are operator commands, never tools."""
import argparse
import json
import sys
from . import CONTRACT_VERSION
from .runtime import MAX_REQUEST_BYTES, approve


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("request", help="Read one versioned JSON request from stdin")
    operator = sub.add_parser("approve", help="Approve the exact reviewed digest")
    operator.add_argument("--vault", required=True)
    operator.add_argument("--state", required=True)
    operator.add_argument("--digest", required=True)
    operator.add_argument("--evidence", required=True)
    setup = sub.add_parser("init", help="Initialize a new empty vault")
    setup.add_argument("--vault", required=True)
    setup.add_argument("--timezone", required=True)
    lifecycle = sub.add_parser("package", help="Preview/apply an allowlisted installation")
    lifecycle.add_argument("action", choices=["install", "remove", "rollback"])
    lifecycle.add_argument("--target", required=True)
    lifecycle.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "request":
            raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
            if len(raw) > MAX_REQUEST_BYTES:
                raise ValueError("request_too_large")
            request = json.loads(raw)
            if request.get("contract_version") != CONTRACT_VERSION:
                raise ValueError("unsupported_contract_version")
            from .operations import dispatch
            result = dispatch(request)
        elif args.command == "approve":
            result = approve(args.vault, args.digest, state=args.state, evidence=args.evidence)
        elif args.command == "init":
            from .package import initialize
            result = initialize(args.vault, args.timezone)
        else:
            from .package import lifecycle
            result = lifecycle(args.action, args.target, apply=args.apply)
        payload = {"contract_version": CONTRACT_VERSION, **result}
        encoded = json.dumps(payload, ensure_ascii=False, default=str)
        if len(encoded.encode()) > MAX_REQUEST_BYTES:
            raise ValueError("result_too_large: use a narrower query")
        print(encoded)
        return 0
    except Exception as exc:
        print(json.dumps({"contract_version": CONTRACT_VERSION, "status": "error",
                          "error": str(exc), "error_type": type(exc).__name__}))
        return 2
