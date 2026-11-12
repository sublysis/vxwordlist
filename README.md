# vxwordlist

A pattern-based wordlist generator for authorized security testing (password auditing, penetration tests, red-team exercises). You describe the *shape* of a password with a compact pattern language, optionally feed in keywords from a source file, and `vxwordlist` writes out every combination.

```bash
vxwordlist -s sourcelist.txt '123$sx2025$!$!$!' -o mylist.txt
```

---

## Table of contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Command-line reference](#command-line-reference)
- [Pattern language](#pattern-language)
- [Examples](#examples)
- [Estimating output size](#estimating-output-size)
- [Design decisions and behavior](#design-decisions-and-behavior)
- [Performance and memory](#performance-and-memory)
- [Troubleshooting](#troubleshooting)
- [Limitations](#limitations)
- [Legal and responsible use](#legal-and-responsible-use)

---

## Features

- Compact pattern syntax with tokens for digits, letters, special characters and source keywords
- Five keyword transformations: lowercase, Capitalized, UPPERCASE, full leet substitution, and mixed-case leet (all variants)
- Free mixing of literals and tokens (`123$sx2025$!$!$!`)
- Multiple keyword tokens in one pattern (passphrase-style combinations)
- Configurable special-character set
- `--estimate` mode to preview the number of candidates and file size before writing anything
- Streaming output: constant RAM usage regardless of list size
- Pure Python 3, standard library only, no dependencies

## Requirements

- Python 3.8 or newer
- Linux, macOS or Windows (the symlink installation below is Linux/macOS; on Windows run `python vxwordlist.py ...`)

## Installation

1. Save the script as `vxwordlist.py`.
2. Make it executable and link it into your `PATH`:

```bash
chmod +x vxwordlist.py
sudo ln -s "$(pwd)/vxwordlist.py" /usr/local/bin/vxwordlist
```

3. Verify:

```bash
vxwordlist --help
```

Without installation you can always run it directly:

```bash
python3 vxwordlist.py -s sourcelist.txt '$Sf2025$!'
```

## Quick start

Create a source file with one keyword per line:

```text
crazyhorse
testword
```

Generate a list:

```bash
vxwordlist -s sourcelist.txt '$Sf2025$!' -o mylist.txt
```

Result (`mylist.txt`, 24 lines):

```text
Crazyhorse2025!
Crazyhorse2025@
Crazyhorse2025#
...
Testword2025+
```

## Command-line reference

```text
vxwordlist [-s FILE] [-o FILE] [--specials CHARS] [--estimate] PATTERN
```

| Argument | Required | Default | Description |
|---|---|---|---|
| `PATTERN` | yes | – | The pattern to expand. **Always wrap it in single quotes** (see [Quoting](#quoting)). |
| `-s`, `--source FILE` | only if the pattern uses a source token | – | File with keywords, one per line. |
| `-o`, `--output FILE` | no | `vxwordlist.txt` | Output file. Existing files are overwritten. |
| `--specials CHARS` | no | `!@#$%&*?-_.+` | Character set used by `$!`. |
| `--estimate` | no | off | Print the candidate count and approximate size, then exit without writing. |

Status messages (candidate count, lines written) go to **stderr**, so the output file stays clean.

Exit codes: `0` success, `130` interrupted with Ctrl+C, non-zero with a message on errors (unreadable source file, source token used without `-s`).

## Pattern language

A token starts with `$`. Everything else is a literal and is copied unchanged.

| Token | Meaning | Number of options |
|---|---|---|
| `$%` | one digit, `0-9` | 10 |
| `$l` | one lowercase letter, `a-z` | 26 |
| `$L` | one uppercase letter, `A-Z` | 26 |
| `$!` | one special character (default set `!@#$%&*?-_.+`, see `--specials`) | 12 by default |
| `$sf` | source keyword, all lowercase | number of keywords |
| `$Sf` | source keyword, first letter capitalized, rest lowercase | number of keywords |
| `$SF` | source keyword, all uppercase | number of keywords |
| `$s%` | source keyword with all letter/digit substitutions applied, everything else lowercase | number of keywords |
| `$sx` | source keyword in leet style: every letter independently takes each of its variants | see below |

### Leet substitution table

Used by `$s%` and `$sx`:

| Letter | `o` | `l` | `i` | `z` | `e` | `a` | `s` | `g` | `t` | `b` | `g` |
|---| --- |---|---|---|---|---|---|---|---|---| --- |
| Digit | `0` | `1` | `1` | `2` | `3` | `4` | `5` | `6` | `7` | `8` | `9` |

Note that `l` and `i` both map to `1`, and `g` maps to `6` and `9`.

### How `$sx` works

For every character of the keyword, the variants are:

1. the lowercase letter
2. the uppercase letter
3. the substituted digit (only if the letter is in the table above)

All combinations are generated. A letter with a substitution has 3 variants, a letter without one has 2, and a non-letter has 1.

Example for `test`: `t` (3: `t`, `T`, `7`) × `e` (3) × `s` (3) × `t` (3) = **81 variants**, including `test`, `TEST`, `7357`, `Te5t`, `t3St`, ...

Example for `crazyhorse`: c(2) · r(2) · a(3) · z(3) · y(2) · h(2) · o(2) · r(2) · s(3) · e(3) = 2⁶ × 3⁴ = **5,184 variants**.

The count grows by up to a factor of 3 per letter, so long keywords get large quickly. Use [`--estimate`](#estimating-output-size) first.

### Literals

Any text that is not a token is passed through as is, so these two patterns generate the same list for a keyword `testword`:

```text
$%$%$Sf2025$!
$%$%Testword2025$!      # only for the keyword "testword", written out manually
```

A lone `$` that is not followed by a valid token name is treated as a literal `$`.

### Quoting

The shell interprets `$!` (PID of the last background job) and `$%`-style sequences before the program sees them. **Always use single quotes:**

```bash
vxwordlist -s words.txt '123$sx2025$!$!$!'     # correct
vxwordlist -s words.txt 123$sx2025$!$!$!       # wrong: the shell mangles the pattern
```

On Windows PowerShell single quotes also work; in `cmd.exe` use double quotes.

## Examples

The examples assume a source file `sourcelist.txt` with the two keywords `crazyhorse` and `testword` unless stated otherwise.

### 1. Two digits, capitalized keyword, year, special character

```bash
vxwordlist -s sourcelist.txt '$%$%$Sf2025$!' -o out.txt
```

Pattern parts: two digits, `$Sf` keyword, literal `2025`, one special character.

Sample lines: `00Crazyhorse2025!`, `88Testword2025#`, `99Testword2025+`
Candidates: 10 × 10 × 2 × 12 = **2,400**

### 2. Literal prefix, full leet variants, three specials

```bash
vxwordlist -s sourcelist.txt '123$sx2025$!$!$!' -o mylist.txt
```

Sample lines: `123Cr42yhors32025!!!`, `123TESTWORD2025@#$`, `1237357word2025---`
Candidates: (5,184 + 1,296) × 12³ = **11,197,440** (≈ 213 MiB). Check with `--estimate` before running this.

### 3. Fully substituted keyword

```bash
vxwordlist -s sourcelist.txt '$s%$%$%$!' -o out.txt
```

For `crazyhorse` the `$s%` result is `cr42yhor53`, for `testword` it is `7357word`.
Sample lines: `cr42yhor53071!`, `7357word99?`
Candidates: 2 × 10 × 10 × 12 = **2,400**

### 4. Lowercase, uppercase and mixed forms of the same keyword

```bash
vxwordlist -s sourcelist.txt '$sf2025!' -o lower.txt
vxwordlist -s sourcelist.txt '$SF2025!' -o upper.txt
vxwordlist -s sourcelist.txt '$Sf2025!' -o capitalized.txt
```

Sample lines: `crazyhorse2025!`, `CRAZYHORSE2025!`, `Crazyhorse2025!`

### 5. Two keywords combined (passphrase style)

```bash
vxwordlist -s sourcelist.txt '$Sf-$Sf$%$%' -o phrases.txt
```

Every keyword is paired with every keyword (including itself).
Sample lines: `Crazyhorse-Testword42`, `Testword-Testword07`
Candidates: 2 × 2 × 10 × 10 = **400**

### 6. No source file needed: pure character patterns

```bash
vxwordlist '$L$l$l$l$l$%$%$!' -o brute.txt
```

Without a source token, `-s` is optional. This pattern has 26 × 26⁴ × 100 × 12 ≈ 14.3 billion candidates, so check the size first.

### 7. Custom special characters

```bash
vxwordlist -s sourcelist.txt '$Sf2025$!' --specials '!#' -o out.txt
```

Only `!` and `#` are used for `$!`, producing `Crazyhorse2025!`, `Crazyhorse2025#`, `Testword2025!`, `Testword2025#`.

### 8. Estimate only

```bash
vxwordlist -s sourcelist.txt '123$sx2025$!$!$!' --estimate
```

Output on stderr:

```text
candidates: 11,197,440  (~213.6 MiB)
```

### 9. Pipe-friendly workflow with deduplication and sorting

```bash
vxwordlist -s sourcelist.txt '$Sf$%$%$!' -o raw.txt
sort -u raw.txt > final.txt
```

## Estimating output size

`--estimate` multiplies the number of options of every token and prints the total together with an approximate file size:

```bash
vxwordlist -s keywords.txt '$sx$%$%$%$%$!' --estimate
```

The size is calculated from the average keyword length of your source file and is only a rough figure (±10-20 %, higher for `$sx`, whose variants have the same length as the keyword). Treat it as an order-of-magnitude check, not an exact value.

Rules of thumb:

| Component | Multiplier |
|---|---|
| each `$%` | ×10 |
| each `$l` / `$L` | ×26 |
| each `$!` | ×12 (default) |
| each `$sf` / `$Sf` / `$SF` / `$s%` | × number of keywords |
| each `$sx` | × Σ variants of all keywords (up to 3ⁿ per keyword) |

## Design decisions and behavior

- **Streaming generation.** Candidates are produced by lazy generators and written directly to disk. RAM usage stays constant even for multi-gigabyte lists.
- **Source file handling.** Keywords are read as UTF-8 (invalid bytes ignored), stripped of whitespace, and deduplicated case-insensitively. Empty lines are skipped. The first spelling of a keyword is kept.
- **Multiple source tokens.** Each source token iterates over all keywords independently, so `$Sf$Sf` yields all ordered pairs.
- **`$Sf` capitalization.** First letter uppercase, the remainder lowercased, regardless of how the keyword is written in the source file.
- **`$s%` is deterministic.** It produces exactly one variant per keyword. Use `$sx` if you want the variants in between.
- **No global deduplication.** Different patterns or keywords can in rare cases produce identical lines. Use `sort -u` if you need a unique list.
- **Output is overwritten.** The output file is opened in write mode. Existing files are replaced without confirmation.
- **Ordering.** Tokens are expanded left to right with the rightmost token changing fastest, like an odometer.

## Performance and memory

- Memory: constant, independent of list size.
- Speed: pure Python, roughly in the order of one to a few million lines per second depending on pattern length and disk speed.
- For very large lists, write to a fast local disk and consider splitting the problem into multiple smaller patterns instead of one huge one.

## Troubleshooting

| Problem | Cause / fix |
|---|---|
| `error: pattern uses source tokens but no keywords available (use -s FILE)` | The pattern contains `$sf`, `$Sf`, `$SF`, `$s%` or `$sx`, but no source file was given or the file is empty. Add `-s FILE`. |
| `error: cannot read source file: ...` | Wrong path or missing permissions. |
| Output contains odd numbers or empty parts instead of `$!` | The pattern was not single-quoted and the shell expanded it. Use single quotes. |
| The list is much larger than expected | Check with `--estimate`. `$sx` and multiple `$l`/`$L` tokens grow very fast. |
| `$` appears literally in the output | A `$` not followed by a valid token name is a literal. Check for typos such as `$sF` (valid are `$sf`, `$Sf`, `$SF`). |
| Token names are case-sensitive | `$sf`, `$Sf` and `$SF` are three different tokens; so are `$l` and `$L`. |

## Limitations

- No built-in rule engine such as hashcat or John rules (reversals, appended years, and so on). Use literals and tokens in the pattern instead.
- No range syntax for digits (`$%{4}`). Repeat the token (`$%$%$%$%`).
- No escape sequence for a literal `$` directly in front of a valid token name.
- No parallelism. Run several instances with different patterns if you need it.

## Legal and responsible use

Use this tool only against systems you own or are explicitly authorized in writing to test. Unauthorized access attempts are illegal in most jurisdictions. The authors accept no liability for misuse.

- Last updated: 11/2026
- Author: Laurent Schueller
- License: MIT

- For authorized penetration testing, lab / training, and network auditing use only.
- Only scan systems you **own** or have **explicit permission** to test.
- For educational purpose suitable.