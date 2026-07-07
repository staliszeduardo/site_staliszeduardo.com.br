#!/usr/bin/env python3
"""
Controlled memory pressure tool for your own VM.

Examples:
  python scripts/burn_memory.py --mb 300 --step-mb 50 --hold 60
  python scripts/burn_memory.py --mb 700 --step-mb 100 --hold 120
  python scripts/burn_memory.py --mb 850 --step-mb 50 --hold 180 --touch-interval 5

Run only on systems you own or have permission to test.
"""

from __future__ import annotations

import argparse
import os
import platform
import sys
import time
from datetime import datetime


BYTES_PER_MB = 1024 * 1024
PAGE_SIZE = 4096


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Consome memoria de forma gradual para testar comportamento da VM/aplicacao."
    )
    parser.add_argument("--mb", type=int, required=True, help="Memoria alvo em MB.")
    parser.add_argument("--step-mb", type=int, default=50, help="Incremento por etapa em MB. Padrao: 50")
    parser.add_argument("--step-delay", type=float, default=2.0, help="Pausa entre etapas em segundos. Padrao: 2")
    parser.add_argument("--hold", type=float, default=60.0, help="Tempo segurando a memoria em segundos. Padrao: 60")
    parser.add_argument(
        "--touch-interval",
        type=float,
        default=10.0,
        help="Intervalo para tocar a memoria e evitar otimizacoes do SO. Padrao: 10",
    )
    parser.add_argument(
        "--max-without-confirm",
        type=int,
        default=512,
        help="Alvo maximo sem --yes-i-know em MB. Padrao: 512",
    )
    parser.add_argument(
        "--yes-i-know",
        action="store_true",
        help="Confirma teste acima de --max-without-confirm.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.mb <= 0:
        raise ValueError("--mb precisa ser maior que 0")
    if args.step_mb <= 0:
        raise ValueError("--step-mb precisa ser maior que 0")
    if args.step_delay < 0:
        raise ValueError("--step-delay nao pode ser negativo")
    if args.hold < 0:
        raise ValueError("--hold nao pode ser negativo")
    if args.touch_interval <= 0:
        raise ValueError("--touch-interval precisa ser maior que 0")
    if args.mb > args.max_without_confirm and not args.yes_i_know:
        raise ValueError(
            f"--mb {args.mb} esta acima de {args.max_without_confirm} MB. "
            "Use --yes-i-know para confirmar."
        )


def get_rss_mb() -> float | None:
    if platform.system() == "Linux":
        try:
            with open("/proc/self/status", "r", encoding="utf-8") as status_file:
                for line in status_file:
                    if line.startswith("VmRSS:"):
                        return int(line.split()[1]) / 1024
        except OSError:
            return None
    return None


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def touch_block(block: bytearray) -> None:
    for index in range(0, len(block), PAGE_SIZE):
        block[index] = (block[index] + 1) % 256


def print_status(message: str, allocated_mb: int) -> None:
    rss = get_rss_mb()
    rss_text = f" rss={rss:.0f}MB" if rss is not None else ""
    print(f"[{now()}] {message} alocado={allocated_mb}MB{rss_text}", flush=True)


def allocate_step(blocks: list[bytearray], step_mb: int) -> None:
    block = bytearray(step_mb * BYTES_PER_MB)
    touch_block(block)
    blocks.append(block)


def main() -> int:
    args = parse_args()

    try:
        validate_args(args)
    except ValueError as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 2

    print("Teste controlado de pressao de memoria")
    print(f"PID:         {os.getpid()}")
    print(f"Alvo:        {args.mb} MB")
    print(f"Incremento:  {args.step_mb} MB")
    print(f"Hold:        {args.hold:.0f}s")
    print("Pare com Ctrl+C para liberar a memoria.\n")

    blocks: list[bytearray] = []
    allocated_mb = 0

    try:
        while allocated_mb < args.mb:
            step_mb = min(args.step_mb, args.mb - allocated_mb)
            allocate_step(blocks, step_mb)
            allocated_mb += step_mb
            print_status("etapa", allocated_mb)
            time.sleep(args.step_delay)

        print_status("alvo atingido", allocated_mb)
        deadline = time.perf_counter() + args.hold
        next_touch = time.perf_counter() + args.touch_interval

        while time.perf_counter() < deadline:
            remaining = max(deadline - time.perf_counter(), 0)
            if time.perf_counter() >= next_touch:
                for block in blocks:
                    touch_block(block)
                print_status(f"segurando memoria restante={remaining:.0f}s", allocated_mb)
                next_touch = time.perf_counter() + args.touch_interval
            time.sleep(0.25)
    except MemoryError:
        print_status("MemoryError: o processo nao conseguiu alocar mais memoria", allocated_mb)
        return 1
    except KeyboardInterrupt:
        print("\nInterrompido pelo usuario. Liberando memoria...")
        return 130
    finally:
        blocks.clear()
        print_status("memoria liberada", 0)

    return 0


if __name__ == "__main__":
    sys.exit(main())
