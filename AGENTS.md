# AGENTS.md

Guidance for developing this repository. Read this before making changes.

## What this project is

A simulator of the SSEM ("Manchester Baby", 1948), the first stored-program computer. Python 3.10+ (uses `match` statements, `X | None` unions); developed against Python 3.14. No third-party dependencies — standard library only (including `curses` for the UI, so running the interactive interface requires a Unix-like terminal).

## Commands

- Run the simulator (interactive curses UI): `python main.py [path/to/program]`
  - Programs: `.asm` (assembly) or `.snp` (binary dump); format is guessed from content, not extension. No argument starts with an empty store.
  - Examples: `samples/ssem/fibonacci.asm`, `samples/ssem/nightmare.snp`
- Run the full test suite: `python -m unittest discover -s tests -p 'test_*.py'` (from the repo root)
  - Tests use `unittest` (not pytest). The VS Code config also runs unittest with discovery from `./tests`.
- Lint changed files with Ruff, if it is available: `ruff check <files>` (from the repo root)
  - Ruff is not a project dependency. Its config is `ruff.toml` at the repo root: the default rule set plus a 120-character line length limit (`E501`).
  - If `ruff` is not installed (`command -v ruff` fails), skip linting silently; do not install it or add tooling unless asked.
- There is no linter/formatter config, no CI, no packaging. Don't add tooling unless asked.

## Architecture

```
main.py                     Entry point: builds Ssem + CommandInterface, runs each in a thread
src/core/                   Machine-agnostic primitives
├── words.py                Words as plain ints (bit 0 = LSB) + b() converter, sign_extend(), to_string(); SSEM bit conventions, two's complement
└── store.py                Store: fixed-size words of fixed length, index-addressed
src/machines/
├── abstractmachine.py      AbstractMachine (ABC) + MachineRuntimeError; contract for any simulated machine
├── ssemmodel.py            SsemModel: *declarative* machine definition (word size/count, opcode layout, Mnemonic enum, speed)
├── assembler.py           Assembler: .asm/.snp loading, format guessing, instruction decoding. Generic: takes any model
├── breakpoints.py          Breakpoints: conditions that pause the machine when they turn true (WordValue: word N holds value V; CiValue: CI takes value N)
└── ssem.py                 Ssem: the machine itself — fetch/decode/execute loop, speed-controlled start()
src/ui/                     Curses interface, split in small modules
├── commandinterface.py     CommandInterface: main loop, input dispatch, store display pad, top/bottom bars, speed meter
├── theme.py                Color pairs and bit representation styles
├── keymap.py               KEYMAP (keys, legend, help descriptions) and the segments derived from it
├── popup.py                Shared pop-up helpers: clamped geometry, guarded box, clipped line writing
├── helppopup.py             HelpPopup: the help pop-up
└── breakpointpopup.py      BreakpointPopup: the breakpoint pop-up (list and typed input)
tests/                      Unit tests
samples/ssem/               Sample programs; samples/ssem/tests/ are the binary fixtures used by functional tests
```

### Key design decisions

- **Machine/model separation.** `SsemModel` describes a machine declaratively (word layout, mnemonics, `instructions_with_data`, `instructions_data_is_address`). `Assembler` and `Ssem` consume any model. The roadmap includes other machines — keep new machines defined as a model + machine pair, and don't bake SSEM constants into generic code.
- **SSEM bit conventions.** Words are plain ints, bit 0 = least significant bit (so the SSEM display order is `format(word, "032b")[::-1]`). Instructions: bits 0-4 = operand address, bits 13-15 = opcode. Negatives are two's complement (`sign_extend()` reads them back). `LDN` loads the *negation*; `JMP` is an *indirect* jump. Don't "fix" these — they are historical accuracy, and the README states accuracy as the project's goal.
- **Run-loop performance.** `Ssem._cycle()` is the hot path: it decodes with precomputed shifts/masks and dispatches through a handler table indexed by the raw opcode (`_execute()` is the mnemonic-level entry for isolated instructions). `last_instruction` is a lazy property built from raw `_last_*` fields — never format a string per cycle in the run loop. `Store.clear()` fills the list in place, so references taken into the run loop stay valid.
- **Threading model.** `main.py` runs the machine and the UI in two threads sharing a `stop_event`; the UI also toggles `machine.stop_flag`. Both must be honored when stopping/stepping. `Ssem.start()` polls `stop_event` between instruction batches and pauses (never exits) while stopped — `main.py` relies on `join()` on both threads at exit.
- **UI performance invariants.** In `src/ui/`: sizes always come from `stdscr.getmaxyx()`, never from `curses.LINES/COLS` (they lag during drag-resize); `_setup_windows` uses `erase()` not `clear()` (avoids flicker); don't use `curses.resizeterm()` (it self-loops KEY_RESIZE); writing the last cell of the last line makes `addstr` error, hence the `cols - 1` truncations and the swallowed `curses.error` in the too-small branch; the top bar must stay a single-line window — a full-screen `newwin` wipes the store area from the virtual screen on its first refresh, since a fresh window copies all its blank lines; a refresh only copies the lines touched since the window's last refresh, so an overlay (the `H` help pop-up, `HelpPopup`) must be `touchwin`-ed before every `noutrefresh` to stay above the pad, and must `erase` its own rectangle when closing (nothing else repaints the regions outside the pad, and the bottom bar needs a `touchwin` to recover its legend); the `B` breakpoint pop-up (`BreakpointPopup`) instead is rebuilt at every frame (its geometry follows the list of breakpoints), so it is erased *before* the pad's `noutrefresh` — a fresh window copies its whole rectangle, keeping it above the pad without `touchwin` and letting the pad repaint the lines its old rectangle blanked; frames are only drawn when something changed (`_needs_redraw`: a key press sets `dirty`, machine movement moves `last_cycle`), so an idle stopped machine draws nothing; with keypad mode on, ncurses holds a lone Esc for the escape-sequence completion delay before returning it, and that wait blocks `getch` even in `nodelay` mode — hence `curses.set_escdelay(25)` in `run_interface` (the default 1 s froze the whole UI on Esc, delivering it only on the next key press; arrow-key sequences are written by the terminal in one piece and match instantly regardless). Comments in those files document these pitfalls — read them before touching display/resize code.
- **UI module split.** The pop-up classes (`HelpPopup`, `BreakpointPopup`) own their window and their drawing; `CommandInterface` opens/closes/composes them and owns the cross-window invariants (compose order in `_draw_screen`, bottom bar `touchwin` on close, resize rebuilds). Keep new UI concerns in the module they belong to rather than growing `commandinterface.py`.
- **Speed pacing.** `Ssem.start()` executes instructions in batches against an absolute deadline (`BATCH_DURATION`) to amortize `sleep()` overshoot and avoid drift. The displayed speed is exponentially smoothed in `_update_displayed_speed`. Preserve this scheme when changing run/step behavior.
- **Assembler strictness.** Assembly lines must carry sequential addresses starting at 0 (e.g. `00 NUM 1`); `;` starts a comment. Errors raise `AssemblerError`, which `main.py` catches to exit with code 1 — keep new parse failures raising `AssemblerError` (not bare exceptions) with a clear message.
- **Breakpoints.** `Ssem.breakpoints` is a plain list read by the machine thread after every cycle and mutated by the UI thread (safe: single list operations are atomic). A `Breakpoint` triggers on a *rising edge* — when its condition turns true — and stays armed until the condition has turned false once; a level trigger would re-pause the machine right after every resume. A breakpoint whose condition already holds at set time pauses the machine on its next cycle. New conditions go in `src/machines/breakpoints.py` as a `Breakpoint` subclass with `_check()` and `description()`; the check in `_cycle()` is guarded by `if self.breakpoints:` so the hot path stays free while none is set. Conditions are duck-typed on the machine: `WordValue` reads `machine.store`, `CiValue` reads `machine.ci` — which, at the end of a cycle, holds the address of the word just executed (or a jump's target), since the SSEM increments CI *before* fetching.

### UI keymap (for testing changes by hand)

`Q`/`Esc` quit, `P` run/stop, `F10` step, `I`/`K` speed up/down, `D` cycle bit display, arrows scroll store, `B` breakpoint pop-up (`T` cycles the condition type — word value or CI — then type the fields, Enter validates, `↑`/`↓` select, `X` delete, `Esc` closes), `H` help pop-up.

## Conventions

- Import style: absolute from repo root (`from src.core.words import b`); tests do the same, so run tests from the repo root.
- No `__init__.py` files in `src/` — packages are implicit; keep it that way.
- Docstrings on public classes/methods, in the existing concise style. Keep the class-level docstring of `Ssem` (it documents the instruction set).
- Tests live in `tests/` mirroring `src/` layout; functional tests build a store from binary words and run the machine to its stop instruction. Prefer extending the existing suite over ad-hoc scripts.
- Bug-fix history shows regressions get a test when practical (e.g. `Store.clear()` cloning, stop-event handling, double-space parsing).
