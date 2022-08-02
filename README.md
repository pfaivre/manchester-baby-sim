# Small-Scale Experimental Machine (SSEM) simulator

The SSEM, also known as the Manchester Baby was the first electronic stored-program computer.

As it is very simple, it is a good subject to study the basic principles of computing.

This program aims at simulating accurately the SSEM while allowing to play with it and tweak it.

# Test it

```sh
python main.py samples/ssem/fibonacci.asm
```
The result will appear on the 28th line in binary.

# Roadmap

- [x] Assembler language linting
- [x] Assembler to binary
- [x] Run the program
- [x] Make the assembler generic by extracting the language definition
- [x] Read binary representation files (.snp)
- [ ] Unit and functional tests (partially done)
- [ ] Interactive interface (work in progress)
- [ ] Improve readability
- [ ] Implement breakpoints: automatically stop at a given condition
- [ ] Implement other machines with this engine
- [ ] Accurate speed execution

# Interface

**Notice**: this is work in progress.
**Notice**: This program does not work on Windows.

This program has an interactive console interface.

The folling "screenshot" of the interface shows a loaded program that computes
the 46th element of the Fibonacci's sequence:
```
[ STATUS: RUNNING ]  [ STEP: 1 ]  [ 01 LDN 31 ]  [ SPEED: 651/700 ips ]
································  CI
································  A

−·······························  00 NUM 1   ;Incremental Value
−−−−−·········−·················  01 LDN 31  ;Load negative of counter
···············−················  02 SUB 0   ;"Increment" our counter
−−−−−········−−·················  03 STO 31  ;Storing negative of counter
−−−−−·········−·················  04 LDN 31  ;Loading the positive of counter
−−−−−········−−·················  05 STO 31  ;Storing positive of counter
−·−−−··········−················  06 SUB 29  ;Substract upper limit
··············−−················  07 CMP     ;Continue if upper limit is not reached
·············−−−················  08 STP     ;Halt
−−·−−·········−·················  09 LDN 27  ;Load negtive of N-th element
··−−−··········−················  10 SUB 28  ;"Add" the N-1 element
·−·−−········−−·················  11 STO 26  ;Store negative of N+1 element
−−·−−·········−·················  12 LDN 27  ;Loads negative of N-th element
··−−−········−−·················  13 STO 28  ;Store negative for new N-1 element
··−−−·········−·················  14 LDN 28  ;Load positive of new N-1 element
··−−−········−−·················  15 STO 28  ;Store positive of new N-1 element
·−·−−·········−·················  16 LDN 26  ;Load positive of new N-th element
−−·−−········−−·················  17 STO 27  ;Store positive of new N-th element
·−−−−···························  18 JMP 30  ;
································  19 JMP 0   ; 0
································  20 JMP 0   ; 0
································  21 JMP 0   ; 0
································  22 JMP 0   ; 0
································  23 JMP 0   ; 0
································  24 JMP 0   ; 0
································  25 JMP 0   ; 0
································  26 NUM 0   ;(N+1) element of Fibonacci sequence
−·······························  27 NUM 1   ;N-th element of Fibonacci sequence
································  28 NUM 0   ;(N-1) element of Fibonacci sequence
·−−−·−··························  29 NUM 46  ;Location to store target index
································  30 NUM 0   ;Starting address of the loop
································  31 NUM 0   ;Counter initialized to zero
```

# Documentation

[Documentation](docs/README.md)

# Bibliography

David Tarnoff, "Programming the 1948 Manchester Baby (SSEM)" https://www.youtube.com/watch?v=o7ozlF5ujUw

Chris P Burton, "The Manchester University Small-Scale Experimental Machine Programmer's Reference Manual" http://curation.cs.manchester.ac.uk/computer50/www.computer50.org/mark1/prog98/ssemref.html

Computer Conservation Society, "SSEM - Technical Overview" https://computerconservationsociety.org/ssemvolunteers/volunteers/introframe.html

David Sharp, "Manchester Baby Simulator" https://davidsharp.com/baby/

Brian Napper, "The Manchester Small Scale Experimental Machine -- "The Baby""
https://web.archive.org/web/20081013180637/http://www.computer50.org/mark1/new.baby.html#specification

# License

This program is licensed under the MIT license.
