#!/usr/bin/env python3
"""
Simple HTTP loop test for a load balancer.

Examples:
  python scripts/test_load_balancer.py http://SEU-DOMINIO.com.br/health
  python scripts/test_load_balancer.py https://SEU-DOMINIO.com.br/ --count 100 --interval 1
  python scripts/test_load_balancer.py http://IP-DO-LB/health --backend-header X-Backend-Server
"""

from __future__ import annotations

import argparse
import ssl
import sys
import time
from datetime import datetime
from http.client import HTTPResponse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Testa disponibilidade/failover de um Load Balancer HTTP/HTTPS."
    )
    parser.add_argument("url", help="URL publica do Load Balancer, ex: https://site.com.br/health")
    parser.add_argument(
        "--count",
        type=int,
        default=0,
        help="Quantidade de requisicoes. Use 0 para rodar ate Ctrl+C. Padrao: 0",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Intervalo em segundos entre requisicoes. Padrao: 2",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Timeout em segundos por requisicao. Padrao: 5",
    )
    parser.add_argument(
        "--backend-header",
        default="X-Backend-Server",
        help="Header usado para identificar a VM/backend. Padrao: X-Backend-Server",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Ignora validacao TLS. Use apenas em teste com certificado temporario.",
    )
    return parser.parse_args()


def read_response(response: HTTPResponse) -> str:
    body = response.read(120)
    return body.decode("utf-8", errors="replace").replace("\n", "\\n")


def request_once(args: argparse.Namespace) -> tuple[bool, str]:
    request = Request(args.url, headers={"User-Agent": "lb-test/1.0"})
    context = ssl._create_unverified_context() if args.insecure else None
    started = time.perf_counter()

    try:
        with urlopen(request, timeout=args.timeout, context=context) as response:
            elapsed_ms = (time.perf_counter() - started) * 1000
            backend = response.headers.get(args.backend_header, "-")
            server = response.headers.get("Server", "-")
            body = read_response(response)
            return (
                True,
                f"OK status={response.status} tempo={elapsed_ms:.0f}ms "
                f"backend={backend} server={server} body={body!r}",
            )
    except HTTPError as error:
        elapsed_ms = (time.perf_counter() - started) * 1000
        return False, f"HTTP_ERRO status={error.code} tempo={elapsed_ms:.0f}ms motivo={error.reason}"
    except URLError as error:
        elapsed_ms = (time.perf_counter() - started) * 1000
        return False, f"FALHA_REDE tempo={elapsed_ms:.0f}ms erro={error.reason}"
    except TimeoutError:
        elapsed_ms = (time.perf_counter() - started) * 1000
        return False, f"TIMEOUT tempo={elapsed_ms:.0f}ms"
    except Exception as error:  # noqa: BLE001 - CLI diagnostic should show unexpected failures.
        elapsed_ms = (time.perf_counter() - started) * 1000
        return False, f"ERRO tempo={elapsed_ms:.0f}ms tipo={type(error).__name__} msg={error}"


def main() -> int:
    args = parse_args()
    successes = 0
    failures = 0
    attempt = 0

    print(f"Testando {args.url}")
    print("Pare com Ctrl+C.\n")

    try:
        while args.count == 0 or attempt < args.count:
            attempt += 1
            ok, message = request_once(args)
            if ok:
                successes += 1
            else:
                failures += 1

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{now}] #{attempt:04d} {message}", flush=True)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nInterrompido pelo usuario.")

    total = successes + failures
    print(f"\nResumo: total={total} ok={successes} falhas={failures}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
