# Small-Scale Experimental Machine (SSEM) simulator specifications

## Main characteristics

- 32 bits program counter called CI
- 32 bits general purpose register called accumulator or A
- 32 words of 32 bits each random access memory called store
- 5 bits addressing
- 7 instructions including jumps, load, store, substract, compare and stop
- Integer stored least significant bit first

## Instruction set

| Op code | Original notation     | Modern notation | Description                                      |
| :------ | :-------------------- | :-------------- | :----------------------------------------------- |
| 000     | CI = S                | JMP             | Indirect jump                                    |
| 100     | CI = CI + S           | JRP             | Relative jump                                    |
| 010     | A = -S                | LDN             | Load negative of value in address S              |
| 110     | S = A                 | STO             | Store accumulator in address S                   |
| 001     | A = A - S             | SUB             | Substract value in address S from accumulator    |
| 101     | A = A - S             | SUB             | Same as SUB                                      |
| 101     | If A < 0, CI = CI + 1 | CMP             | Skip next instruction if accumulator is negative |
| 111     | Stop                  | STP             | Halt the program                                 |

Format of an instruction (example here is STO 26):
```
._.__........__.................

-----        ---
  ^           ^
  |           `--- Operation code
  `--------------- S: address passed to the instruction
```
The rest of the space in the instruction is not used.
