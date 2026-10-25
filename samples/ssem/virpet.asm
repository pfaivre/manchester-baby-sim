; virpet.asm - Virtual pet, like the "Tamagotchi" children's toy The
; virtual pet must constantly be fed.  As long as it has sufficient
; food, it shows a happy face, and a full belly.  When it runs out, it
; shows a sad face and a slim profile.  You can then pause the machine
; to give it more food by loading a number, e.g. 512, into line 22.  It
; will then return to a happy face until it runs out again. By Achut
; Reddy, USA.

00 NUM 0
01 LDN 22
02 SUB 27
03 STO 25
04 LDN 25
05 STO 22
06 CMP
07 JMP 0
08 LDN 23
09 STO 31
10 LDN 24
11 STO 30
12 LDN 0
13 STO 22
14 LDN 22
15 CMP
16 JRP 26
17 LDN 23
18 STO 30
19 LDN 24
20 STO 31
21 JMP 0
22 NUM 1000
23 NUM -35651904
24 NUM -29360256
25 NUM 0
26 NUM -3
27 NUM -1
28 NUM 20971648
29 NUM 448
30 NUM 35651904
31 NUM 29360256
