#!/usr/bin/env python3

# Copyright 2026 Pouria Rezaei <Pouria.rz@outlook.com>
# All rights reserved.
#
# Redistribution and use of this script, with or without modification, is
# permitted provided that the following conditions are met:
#
# 1. Redistributions of this script must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#
#  THIS SOFTWARE IS PROVIDED BY THE AUTHOR "AS IS" AND ANY EXPRESS OR IMPLIED
#  WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
#  MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO
#  EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
#  PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
#  OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
#  WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
#  OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
#  ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import annotations
import ipaddress
import sys
from pathlib import Path

INVALID_EXAMPLE_LIMIT = 15

def prompt_path(prompt: str) -> str:
	while True:
		value = input(prompt).strip().strip('"')
		if value:
			return value
		print("Please enter a non-empty path.")


def parse_network_entry(text: str):
	stripped = text.split("#", 1)[0].strip()
	if not stripped:
		return None

	try:
		network = ipaddress.ip_network(stripped, strict=False)
	except ValueError:
		return None

	if network.version not in (4, 6):
		return None

	return network


def sort_key(net):
	return (net.version, int(net.network_address), net.prefixlen)


def collapse_and_sort(networks):
	v4 = [net for net in networks if isinstance(net, ipaddress.IPv4Network)]
	v6 = [net for net in networks if isinstance(net, ipaddress.IPv6Network)]

	collapsed_v4 = sorted(ipaddress.collapse_addresses(v4), key=sort_key)
	collapsed_v6 = sorted(ipaddress.collapse_addresses(v6), key=sort_key)

	return collapsed_v4, collapsed_v6


def write_output(output_file: Path, v4_networks, v6_networks) -> None:
	with output_file.open("w", encoding="utf-8", newline="\n") as f:
		for net in v4_networks:
			f.write(f"{net.with_prefixlen}\n")
		for net in v6_networks:
			f.write(f"{net.with_prefixlen}\n")


def main() -> int:
	input_path = prompt_path("Enter INPUT file path: ")
	output_path = prompt_path("Enter OUTPUT file path: ")

	input_file = Path(input_path).expanduser()
	output_file = Path(output_path).expanduser()

	if not input_file.is_file():
		print(f"Error: input file not found: {input_file}", file=sys.stderr, flush=True)
		return 1

	try:
		output_file.parent.mkdir(parents=True, exist_ok=True)
	except OSError as exc:
		print(
			f"Error: could not create output directory '{output_file.parent}': {exc}",
			file=sys.stderr,
			flush=True,
		)
		return 1

	valid_networks = []
	invalid_count = 0
	skipped_blank_or_comment = 0
	invalid_examples: list[tuple[int, str]] = []

	print("Reading and parsing input file...", flush=True)

	try:
		with input_file.open("r", encoding="utf-8", errors="replace") as f:
			for line_number, raw_line in enumerate(f, start=1):
				stripped = raw_line.split("#", 1)[0].strip()

				if not stripped:
					skipped_blank_or_comment += 1
					continue

				network = parse_network_entry(raw_line)
				if network is not None:
					valid_networks.append(network)
					continue

				invalid_count += 1
				if len(invalid_examples) < INVALID_EXAMPLE_LIMIT:
					invalid_examples.append((line_number, raw_line.strip()))

	except OSError as exc:
		print(f"Error reading input file: {exc}", file=sys.stderr, flush=True)
		return 1

	if not valid_networks:
		print("No valid IPv4 or IPv6 entries found.", flush=True)
		try:
			output_file.write_text("", encoding="utf-8")
		except OSError as exc:
			print(f"Error writing output file: {exc}", file=sys.stderr, flush=True)
			return 1

		if invalid_count:
			print(f"Skipped {invalid_count} invalid line(s).", flush=True)
		if skipped_blank_or_comment:
			print(f"Ignored {skipped_blank_or_comment} blank/comment line(s).", flush=True)
		return 0

	v4_before = sum(1 for net in valid_networks if isinstance(net, ipaddress.IPv4Network))
	v6_before = len(valid_networks) - v4_before

	print(
		f"Found {v4_before:,} IPv4 and {v6_before:,} IPv6 valid entr"
		f"{'y' if len(valid_networks) == 1 else 'ies'}.",
		flush=True,
	)
	print("Merging overlapping/adjacent ranges and removing duplicates...", flush=True)

	try:
		v4_collapsed, v6_collapsed = collapse_and_sort(valid_networks)
	except ValueError as exc:
		print(f"Error while merging networks: {exc}", file=sys.stderr, flush=True)
		return 1

	print(
		f"Writing {len(v4_collapsed):,} IPv4 + {len(v6_collapsed):,} IPv6 merged CIDR block(s)...",
		flush=True,
	)

	try:
		write_output(output_file, v4_collapsed, v6_collapsed)
	except OSError as exc:
		print(f"Error writing output file: {exc}", file=sys.stderr, flush=True)
		return 1

	print(f"\nDone! Output written to: {output_file}", flush=True)
	print(f"   Input  → {v4_before:,} IPv4 + {v6_before:,} IPv6 valid entr"
		  f"{'y' if len(valid_networks) == 1 else 'ies'}")
	print(
		f"   Output → {len(v4_collapsed):,} IPv4 + {len(v6_collapsed):,} IPv6 CIDR block(s)"
	)

	if invalid_count:
		print(f"\nSkipped {invalid_count} invalid line(s).", flush=True)
		if invalid_examples:
			print("First few invalid lines:", flush=True)
			for line_number, text in invalid_examples:
				print(f"  Line {line_number}: {text!r}", flush=True)

	if skipped_blank_or_comment:
		print(f"\nIgnored {skipped_blank_or_comment} blank/comment line(s).", flush=True)

	return 0


if __name__ == "__main__":
	try:
		raise SystemExit(main())
	except KeyboardInterrupt:
		print("\nCancelled by user.", file=sys.stderr, flush=True)
		raise SystemExit(130) from None
