# Small-Scale Experimental Machine (SSEM) simulator specifications

## Main characteristics

- 32 bits program counter called CI
- 32 bits general purpose register called accumulator or A
- 32 words of 32 bits each random access memory called store
- 5 bits addressing
- 7 instructions including jumps, load, store, substract, compare and stop
- Integer stored least significant bit first

## Instruction set

| Op code | Original notation | Modern notation | Description                                        |
| :------ | :---------------- | :-------------- | :------------------------------------------------- |
| 000     | s,C               | JMP             | Indirect jump                                      |
| 100     | c+s,C             | JRP             | Relative jump                                      |
| 010     | -s,A              | LDN             | Load negative of value in address S to accumulator |
| 110     | a,S               | STO             | Store accumulator in address S                     |
| 001     | a-s, A            | SUB             | Substract value in address S from accumulator      |
| 101     | -                 | -               | Same as SUB                                        |
| 101     | Test              | CMP             | Skip next instruction if accumulator is negative   |
| 111     | Stop              | STP             | Halt the program                                   |

Format of an instruction (example here is STO 26):
```
._.__........__.................

-----        ---
  ^           ^
  |           `--- Operation code
  `--------------- S: address passed to the instruction
```
The other bits are not used.
