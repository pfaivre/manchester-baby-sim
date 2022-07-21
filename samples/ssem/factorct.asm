; The first program was written by Tom Kilburn. It was a program to find the highest proper factor of any number a;
; this was done by trying every integer b from a-1 downward until one was found that divided exactly into a.
; The necessary divisions were done not by long division but by repeated subtraction of b
; (because the "Baby" only had a hardware subtractor).
;
; https://web.archive.org/web/20081006200609/http://www.computer50.org/mark1/firstprog.html

; When stopped, the answer will appear on line 27
; With the number entered in the present file, it should be 131072

00 JMP 0    ;
01 LDN 24   ; -24 to C
02 STO 26   ; C to 26
03 LDN 26   ; -26 to C
04 STO 27   ; C to 27
05 LDN 23   ; -23 to C
06 SUB 27   ; Sub 27
07 CMP      ; Test
08 JRP 20   ; Add 20 to [...]
09 SUB 26   ; Sub 26
10 STO 25   ; C to 25
11 LDN 25   ; -25 to C
12 CMP      ; Test
13 STP      ; Stop
14 LDN 26   ; -26 to C
15 SUB 21   ; Sub 21
16 STO 27   ; C to 27
17 LDN 27   ; -27 to C
18 STO 26   ; C to 26
19 JMP 22   ; 22 to [...]
20 NUM -3   ;
21 NUM 1    ;
22 NUM 4    ;
23 NUM -262144  ; Opposit of the following number
24 NUM 262143   ; the number to find the highest factor of
25 NUM 0    ;
26 NUM 0    ;
27 NUM 0    ; This line will hold the answer when finished
28 NUM 0    ;
29 NUM 0    ;
30 NUM 0    ;
31 NUM 0    ;
