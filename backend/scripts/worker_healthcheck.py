"""Docker healthcheck CLI for producer and consumer readiness."""

from __future__ import annotations

import argparse

from scripts.worker_health import check_worker_health


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("service", choices=("productor", "consumidor"))
    service = parser.parse_args().service
    healthy, message = check_worker_health(service)
    print(message)
    return 0 if healthy else 1


if __name__ == "__main__":
    raise SystemExit(main())
