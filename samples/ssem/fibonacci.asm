; This programme is written for the Small-Scale Experimental Machine (SSEM)
; It computes a given iteration of the Fibonacci sequence (specified in address 29)
;
; By David Tarnoff "Programming the Manchester Baby - Part 2" https://www.youtube.com/watch?v=y8jTDTe9yrg

00 NUM 1    ;Incremental Value
01 LDN 31   ;Load negative of counter
02 SUB 0    ;"Increment" our counter
03 STO 31   ;Storing negative of counter
04 LDN 31   ;Loading the positive of counter
05 STO 31   ;Storing positive of counter
06 SUB 29   ;Substract upper limit
07 CMP      ;Jump over next instruction if upper limit is reached
08 STP      ;Stop
09 LDN 27   ;Load negtive of N-th element
10 SUB 28   ;"Add" the N-1 element
11 STO 26   ;Store negative of N+1 element
12 LDN 27   ;Loads negative of N-th element
13 STO 28   ;Store negative for new N-1 element
14 LDN 28   ;Load positive of new N-1 element
15 STO 28   ;Store positive of new N-1 element
16 LDN 26   ;Load positive of new N-th element
17 STO 27   ;Store positive of new N-th element
18 JMP 30   ;
19 JMP 0    ; 0
20 JMP 0    ; 0
21 JMP 0    ; 0
22 JMP 0    ; 0
23 JMP 0    ; 0
24 JMP 0    ; 0
25 JMP 0    ; 0
26 NUM 0    ;(N+1) element of Fibonacci sequence
27 NUM 1    ;N-th element of Fibonacci sequence
28 NUM 0    ;(N-1) element of Fibonacci sequence
29 NUM 46   ;Location to store target index
30 NUM 0    ;Starting address of the loop
31 NUM 0    ;Counter initialized to zero
