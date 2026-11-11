#!/usr/bin/env python3
"""
vxwordlist

Pattern-based wordlist generator for ctf and pentesting. With estimation of expected wordlist size to tailor your approach.
   
Last updated: 11/2026
GitHub: https://github.com/sublysis/vxwordlist
Author: Laurent Schueller, https://sublysis.github.io
License: MIT

For authorized penetration testing, lab / training, and network auditing use only.
For educational purpose suitable.
Unauthorized scanning may be illegal.
The authors accept no liability for misuse.
"""

import argparse
import itertools
import sys

DIGITS = "0123456789"
LOWER = "abcdefghijklmnopqrstuvwxyz"
UPPER = LOWER.upper()
DEFAULT_SPECIALS = "!@#$%&*?-_.+"
LEET = {
"l": "1", 
"i": "1", 
"z": "2", 
"e": "3", 
"a": "4",
"s": "5", 
"g": "6", 
"t": "7", 
"b": "8"}

# Token names after "$". Two-char names must be checked before one-char names.
TWO_CHAR = {"sf", "Sf", "SF", "s%", "sx"}
ONE_CHAR = {"%", "l", "L", "!"}


def tokenize(pattern):
    """Split pattern into ('lit', text) and ('tok', name) items."""
    out, lit, i = [], [], 0
    while i < len(pattern):
        if pattern[i] == "$":
            if pattern[i + 1:i + 3] in TWO_CHAR:
                name, step = pattern[i + 1:i + 3], 3
            elif pattern[i + 1:i + 2] in ONE_CHAR:
                name, step = pattern[i + 1], 2
            else:
                lit.append("$")  # lone "$" is a literal
                i += 1
                continue
            if lit:
                out.append(("lit", "".join(lit)))
                lit = []
            out.append(("tok", name))
            i += step
        else:
            lit.append(pattern[i])
            i += 1
    if lit:
        out.append(("lit", "".join(lit)))
    return out


def char_variants(c):
    lo = c.lower()
    v = [lo]
    if c.upper() != lo:
        v.append(c.upper())
    if lo in LEET:
        v.append(LEET[lo])
    return v


def leet_sub(word):
    return "".join(LEET.get(c, c) for c in word.lower())


def sx_variants(word):
    return ("".join(p) for p in itertools.product(*(char_variants(c) for c in word)))


def sx_count(word):
    n = 1
    for c in word:
        n *= len(char_variants(c))
    return n


def build_options(kind, name, words, specials):
    """Return (lazy options factory, size) for one token."""
    if kind == "lit":
        return (lambda: iter([name])), 1
    simple = {
        "%": (DIGITS, len(DIGITS)),
        "l": (LOWER, len(LOWER)),
        "L": (UPPER, len(UPPER)),
        "!": (specials, len(specials)),
    }
    if name in simple:
        chars, size = simple[name]
        return (lambda: iter(chars)), size

    if name == "sf":
        return (lambda: (w.lower() for w in words)), len(words)
    if name == "Sf":
        return (lambda: (w[:1].upper() + w[1:].lower() for w in words)), len(words)
    if name == "SF":
        return (lambda: (w.upper() for w in words)), len(words)
    if name == "s%":
        return (lambda: (leet_sub(w) for w in words)), len(words)
    if name == "sx":
        return (lambda: itertools.chain.from_iterable(sx_variants(w) for w in words)), \
               sum(sx_count(w) for w in words)
    raise ValueError(f"unknown token ${name}")


def expand(opts, i=0, prefix=""):
    if i == len(opts):
        yield prefix
        return
    for o in opts[i]():
        yield from expand(opts, i + 1, prefix + o)


def load_words(path):
    seen, words = set(), []
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            w = line.strip()
            if w and w.lower() not in seen:
                seen.add(w.lower())
                words.append(w)
    return words


def main():
    ap = argparse.ArgumentParser(
        prog="vxwordlist",
        description="Pattern-based wordlist generator. Quote the pattern in single quotes!",
        epilog="Tokens: $%% digit | $l lower | $L upper | $! special | "
               "$sf word lower | $Sf Capitalized | $SF UPPER | "
               "$s%% full leet substitution | $sx leet mixed-case (all variants)")
    ap.add_argument("pattern", help="pattern, e.g. '123$sx2025$!$!$!'")
    ap.add_argument("-s", "--source", help="file with keywords, one per line")
    ap.add_argument("-o", "--output", default="vxwordlist.txt",
                    help="output file (default: vxwordlist.txt)")
    ap.add_argument("--specials", default=DEFAULT_SPECIALS,
                    help=f"character set for $! (default: {DEFAULT_SPECIALS})")
    ap.add_argument("--estimate", action="store_true",
                    help="only print number of candidates and file size, then exit")
    args = ap.parse_args()

    tokens = tokenize(args.pattern)
    needs_source = any(k == "tok" and n in {"sf", "Sf", "SF", "s%", "sx"} for k, n in tokens)

    words = []
    if args.source:
        try:
            words = load_words(args.source)
        except OSError as e:
            sys.exit(f"error: cannot read source file: {e}")
    if needs_source and not words:
        sys.exit("error: pattern uses source tokens but no keywords available (use -s FILE)")

    opts, total = [], 1
    for kind, name in tokens:
        factory, size = build_options(kind, name, words, args.specials)
        opts.append(factory)
        total *= size

    # rough size: pattern length estimate (+1 newline); source words vary, so approximate
    avg_word = (sum(map(len, words)) / len(words)) if words else 0
    avg_len = sum(len(n) if k == "lit"
                  else (avg_word if n in {"sf", "Sf", "SF", "s%", "sx"} else 1)
                  for k, n in tokens) + 1
    print(f"candidates: {total:,}  (~{total * avg_len / 1024**2:,.1f} MiB)", file=sys.stderr)
    if args.estimate:
        return

    count = 0
    with open(args.output, "w", encoding="utf-8", buffering=1024 * 1024) as f:
        for line in expand(opts):
            f.write(line + "\n")
            count += 1
    print(f"written: {count:,} lines -> {args.output}", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)