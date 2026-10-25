; diffeqt.asm - Calculate points on a parabola using a difference
; equation, and draw the parabola. By Magnus Olsson, Sweden.
;
; The Baby's only output is the CRT display of its store: 32 lines of
; 32 dots, one dot per bit (least significant bit on the left). This
; program draws by setting bits in the store itself, always in bits 16
; to 31 - above the opcode/operand bits - so it can draw over its own
; code without corrupting it:
;   - Line 29 holds a single 1 bit, the x coordinate of the point to
;     plot. Lines 01-07 double it every iteration, so the dot walks
;     from column 18 to column 31, one column per loop.
;   - Lines 08-12 then set that bit in the store line chosen by the
;     difference equation (the store line number is the y coordinate):
;     rows 22, 16, 11, 7, 4, 2, 1, 1, 2, 4, 7, 11, 16, 22 - a parabola.
;   - y is not computed directly: line 28 holds the first difference d,
;     and the "store line" operands of the instructions at lines 08 and
;     12 are rewritten every iteration so the code follows the curve
;     (self-modifying code).
;   - The Baby has no ADD instruction: the idiom "negate, subtract,
;     store, negate" (with line 30 as scratch) computes X + Y.

00 NUM 0          ; Zero word, never executed: the machine starts at
                  ; line 01, and the jump at line 25 resumes there too
01 LDN 29         ; A = -x: negate the marker in line 29
02 SUB 29         ; A = -(x + x) = -2x: double the marker, still negated
03 STO 29         ; x = -2x
04 CMP            ; While A is negative (x still a positive power of
                  ; two), skip the stop below: the dot has not yet
                  ; reached the end of the line
05 STP            ; Stop the machine: doubling pushed the marker past
                  ; the last bit, all 14 points have been plotted
06 LDN 29         ; A = 2x: negate the doubled marker back
07 STO 29         ; x = 2x: the dot in line 29 has moved one column left
                  ; (2^18, 2^19, ... 2^31): the next point to plot
08 LDN 22         ; A = -line[op]: read the store line to plot in, where
                  ; "op" is the y coordinate. This operand is rewritten
                  ; every iteration by lines 13-17 (initially op = 22)
09 SUB 29         ; A = -line[op] - x
10 STO 30         ; line 30 = -(line[op] + x), line 30 is scratch
11 LDN 30         ; A = line[op] + x
12 STO 22         ; line[op] = line[op] + x: set bit x in line op, i.e.
                  ; draw one dot of the parabola at (x, op). This
                  ; operand is also rewritten every iteration (line 19)
13 LDN 8          ; A = -line 8: line 8 holds the instruction "LDN op",
                  ; so its numeric value carries the y coordinate
14 SUB 28         ; A = -line8 - d, with d the first difference (line 28)
15 STO 30         ; line 30 = -(line8 + d)
16 LDN 30         ; A = line8 + d
17 STO 8          ; line 8 = "LDN op + d": the y coordinate advances by
                  ; the first difference (op: 22, 16, 11, 7, 4, 2, 1, ...)
18 SUB 27         ; A = line8 + 8192: add 1 into the opcode bits (13-15),
                  ; turning "LDN op" (opcode 2) into "STO op" (opcode 3)
19 STO 12         ; line 12 becomes "STO op": rebuild the store instruction
                  ; used at line 12 with the new y coordinate
20 LDN 28         ; A = -d
21 SUB 26         ; A = -d - 1
22 STO 28         ; d = -d - 1
23 LDN 28         ; A = d + 1
24 STO 28         ; d = d + 1: increment the first difference by the
                  ; second difference (1) - this is what makes the
                  ; sequence of points curve into a parabola
25 JMP 31         ; Back to the top of the loop: CI takes the content of
                  ; line 31 (0) and is incremented before the next
                  ; fetch, so execution resumes at line 01
26 NUM 1          ; The second difference of the curve: added to d by
                  ; lines 20-24 at every iteration
27 NUM -8192      ; -2^13: subtracted at line 18, it adds 8192 = 2^13,
                  ; i.e. +1 in the opcode bits, turning LDN into STO
28 NUM -6         ; d, the first difference: starts at -6 and grows by 1
                  ; each iteration (-6, -5, -4, ...), moving op through
                  ; 22, 16, 11, 7, 4, 2, 1, 1, 2, 4, ... (a parabola)
29 NUM 131072     ; 2^17, the x marker: lines 01-07 double it every
                  ; iteration, moving the dot from column 18 to 31;
                  ; when it falls off the end, lines 04-05 stop the run
30 NUM 0          ; Scratch line used to negate values in the addition
                  ; idiom
31 NUM 0          ; Holds 0: target of the JMP at line 25 (the jump
                  ; resumes execution at line 01)
