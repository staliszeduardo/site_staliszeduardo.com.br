#!/usr/bin/env python3
"""
Controlled HTTP stress test for your own site/load balancer.

Examples:
  python scripts/stress_load_balancer.py https://SEU-DOMINIO.com.br/ --duration 60 --rps 20 --concurrency 20
  python scripts/stress_load_balancer.py https://SEU-DOMINIO.com.br/health --duration 120 --rps 50 --concurrency 50
  python scripts/stress_load_balancer.py https://SEU-DOMINIO.com.br/ --duration 60 --rps 30 --concurrency 30 --cache-buster

Use only against systems you own or have permission to test.
"""

from __future__ import annotations

import argparse
import os
import ssl
import sys
import time
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import datetime
from statistics import mean
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl
from urllib.request import Request, urlopen


DEFAULT_SAFE_CONCURRENCY_LIMIT = 1000


@dataclass(frozen=True)
class Result:
    ok: bool
    status: str
    elapsed_ms: float
    error: str
    cf_cache_status: str
    backend: str


class Stats:
    def __init__(self) -> None:
        self.started_at = time.perf_counter()
        self.total = 0
        self.ok = 0
        self.failed = 0
        self.statuses: Counter[str] = Counter()
        self.errors: Counter[str] = Counter()
        self.cf_cache: Counter[str] = Counter()
        self.backends: Counter[str] = Counter()
        self.latencies_ms: list[float] = []

    def add(self, result: Result) -> None:
        self.total += 1
        self.ok += int(result.ok)
        self.failed += int(not result.ok)
        self.statuses[result.status] += 1
        if result.error:
            self.errors[result.error] += 1
        if result.cf_cache_status != "-":
            self.cf_cache[result.cf_cache_status] += 1
        if result.backend != "-":
            self.backends[result.backend] += 1
        self.latencies_ms.append(result.elapsed_ms)

    def snapshot(self) -> dict[str, object]:
        elapsed = max(time.perf_counter() - self.started_at, 0.001)
        return {
            "elapsed": elapsed,
            "total": self.total,
            "ok": self.ok,
            "failed": self.failed,
            "rps": self.total / elapsed,
            "avg_ms": mean(self.latencies_ms) if self.latencies_ms else 0,
            "p50_ms": percentile(self.latencies_ms, 50),
            "p95_ms": percentile(self.latencies_ms, 95),
            "p99_ms": percentile(self.latencies_ms, 99),
            "statuses": self.statuses,
            "errors": self.errors,
            "cf_cache": self.cf_cache,
            "backends": self.backends,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Teste de stress HTTP controlado para site/Load Balancer."
    )
    parser.add_argument("url", help="URL publica do site ou Load Balancer.")
    parser.add_argument("--duration", type=float, default=60.0, help="Duracao em segundos. Padrao: 60")
    parser.add_argument("--rps", type=float, default=10.0, help="Requisicoes por segundo desejadas. Padrao: 10")
    parser.add_argument("--concurrency", type=int, default=10, help="Requisicoes simultaneas. Padrao: 10")
    parser.add_argument(
        "--allow-high-concurrency",
        action="store_true",
        help=f"Permite concorrencia acima de {DEFAULT_SAFE_CONCURRENCY_LIMIT}. Use com cuidado.",
    )
    parser.add_argument("--timeout", type=float, default=5.0, help="Timeout por requisicao. Padrao: 5")
    parser.add_argument("--method", choices=("GET", "HEAD"), default="GET", help="Metodo HTTP. Padrao: GET")
    parser.add_argument(
        "--report-interval",
        type=float,
        default=5.0,
        help="Intervalo do relatorio em segundos. Padrao: 5",
    )
    parser.add_argument(
        "--cache-buster",
        action="store_true",
        help="Adiciona query string unica por request para evitar medir apenas cache.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Envia Cache-Control: no-cache. Use com cuidado: aumenta chance de chegar no origin.",
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


def percentile(values: list[float], percent: int) -> float:
    if not values:
        return 0.0

    ordered = sorted(values)
    index = (len(ordered) - 1) * (percent / 100)
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def with_cache_buster(url: str, sequence: int) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["_stress"] = f"{int(time.time())}-{sequence}"
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def request_once(args: argparse.Namespace, sequence: int) -> Result:
    url = with_cache_buster(args.url, sequence) if args.cache_buster else args.url
    headers = {"User-Agent": "site-stress-test/1.0"}
    if args.no_cache:
        headers["Cache-Control"] = "no-cache"
        headers["Pragma"] = "no-cache"

    request = Request(url, headers=headers, method=args.method)
    context = ssl._create_unverified_context() if args.insecure else None
    started = time.perf_counter()

    try:
        with urlopen(request, timeout=args.timeout, context=context) as response:
            if args.method == "GET":
                response.read(4096)
            elapsed_ms = (time.perf_counter() - started) * 1000
            status = str(response.status)
            return Result(
                ok=200 <= response.status < 400,
                status=status,
                elapsed_ms=elapsed_ms,
                error="",
                cf_cache_status=response.headers.get("CF-Cache-Status", "-"),
                backend=response.headers.get(args.backend_header, "-"),
            )
    except HTTPError as error:
        elapsed_ms = (time.perf_counter() - started) * 1000
        return Result(
            ok=False,
            status=str(error.code),
            elapsed_ms=elapsed_ms,
            error=f"HTTP_{error.code}",
            cf_cache_status=error.headers.get("CF-Cache-Status", "-"),
            backend=error.headers.get(args.backend_header, "-"),
        )
    except TimeoutError:
        elapsed_ms = (time.perf_counter() - started) * 1000
        return Result(False, "TIMEOUT", elapsed_ms, "TIMEOUT", "-", "-")
    except URLError as error:
        elapsed_ms = (time.perf_counter() - started) * 1000
        reason = str(error.reason).splitlines()[0]
        return Result(False, "REDE", elapsed_ms, reason[:80], "-", "-")
    except Exception as error:  # noqa: BLE001 - CLI diagnostic should show unexpected failures.
        elapsed_ms = (time.perf_counter() - started) * 1000
        return Result(False, "ERRO", elapsed_ms, type(error).__name__, "-", "-")


def compact_counter(counter: Counter[str], limit: int = 6) -> str:
    if not counter:
        return "-"
    return ", ".join(f"{key}:{value}" for key, value in counter.most_common(limit))


def print_report(stats: Stats, sent: int, in_flight: int, final: bool = False) -> None:
    snap = stats.snapshot()
    title = "FINAL" if final else datetime.now().strftime("%H:%M:%S")
    print(
        f"[{title}] enviados={sent} completos={snap['total']} em_voo={in_flight} "
        f"ok={snap['ok']} falhas={snap['failed']} rps_real={snap['rps']:.1f} "
        f"avg={snap['avg_ms']:.0f}ms p50={snap['p50_ms']:.0f}ms "
        f"p95={snap['p95_ms']:.0f}ms p99={snap['p99_ms']:.0f}ms",
        flush=True,
    )
    print(f"        status: {compact_counter(snap['statuses'])}", flush=True)
    print(f"        erros:  {compact_counter(snap['errors'])}", flush=True)
    print(f"        cf:     {compact_counter(snap['cf_cache'])}", flush=True)
    print(f"        vm:     {compact_counter(snap['backends'])}", flush=True)


def validate_args(args: argparse.Namespace) -> None:
    if args.duration <= 0:
        raise ValueError("--duration precisa ser maior que 0")
    if args.rps <= 0:
        raise ValueError("--rps precisa ser maior que 0")
    if args.concurrency <= 0:
        raise ValueError("--concurrency precisa ser maior que 0")
    if args.concurrency > DEFAULT_SAFE_CONCURRENCY_LIMIT and not args.allow_high_concurrency:
        raise ValueError(
            f"--concurrency acima de {DEFAULT_SAFE_CONCURRENCY_LIMIT} pode esgotar sockets locais. "
            "Reduza a concorrencia ou use --allow-high-concurrency se quiser assumir esse risco."
        )
    if args.timeout <= 0:
        raise ValueError("--timeout precisa ser maior que 0")
    if args.report_interval <= 0:
        raise ValueError("--report-interval precisa ser maior que 0")


def print_local_capacity_hint(args: argparse.Namespace) -> None:
    cpu_count = os.cpu_count() or 1
    if args.concurrency > cpu_count * 100:
        print(
            "Aviso: concorrencia muito alta para um gerador de carga local. "
            "Se aparecer WinError 10055, o limite atingido provavelmente e do cliente Windows.",
            flush=True,
        )
    if args.cache_buster or args.no_cache:
        print(
            "Aviso: cache-buster/no-cache aumenta a chance de trafego chegar ao origin. "
            "Suba a carga em etapas pequenas.",
            flush=True,
        )


def collect_done(done: set[Future[Result]], stats: Stats) -> None:
    for future in done:
        stats.add(future.result())


def main() -> int:
    args = parse_args()

    try:
        validate_args(args)
    except ValueError as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 2

    print("Teste de stress controlado")
    print(f"URL:          {args.url}")
    print(f"Duracao:      {args.duration:.0f}s")
    print(f"RPS alvo:     {args.rps:.1f}")
    print(f"Concorrencia: {args.concurrency}")
    print(f"Metodo:       {args.method}")
    print(f"Cache buster: {'sim' if args.cache_buster else 'nao'}")
    print_local_capacity_hint(args)
    print("Pare com Ctrl+C.\n")

    stats = Stats()
    sent = 0
    in_flight: set[Future[Result]] = set()
    started = time.perf_counter()
    deadline = started + args.duration
    next_request_at = started
    next_report_at = started + args.report_interval

    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        try:
            while time.perf_counter() < deadline:
                now = time.perf_counter()

                if now >= next_report_at:
                    print_report(stats, sent, len(in_flight))
                    next_report_at = now + args.report_interval

                if len(in_flight) >= args.concurrency:
                    done, in_flight = wait(in_flight, timeout=0.05, return_when=FIRST_COMPLETED)
                    collect_done(done, stats)
                    continue

                if now < next_request_at:
                    done, in_flight = wait(
                        in_flight,
                        timeout=min(0.05, next_request_at - now),
                        return_when=FIRST_COMPLETED,
                    )
                    collect_done(done, stats)
                    continue

                sent += 1
                in_flight.add(executor.submit(request_once, args, sent))
                next_request_at = started + (sent / args.rps)

            while in_flight:
                done, in_flight = wait(in_flight, timeout=0.2, return_when=FIRST_COMPLETED)
                collect_done(done, stats)
        except KeyboardInterrupt:
            print("\nInterrompido pelo usuario. Aguardando requests em voo terminarem...")
            while in_flight:
                done, in_flight = wait(in_flight, timeout=0.2, return_when=FIRST_COMPLETED)
                collect_done(done, stats)

    print()
    print_report(stats, sent, 0, final=True)
    return 0 if stats.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
