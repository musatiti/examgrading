def grade_demo():
    return """Demo Mode (Simulated AI Result)

Total Score: 23.5 / 30

Question 1 :
 Student: a c d a b d a c a d
 Key: b d d a b a a c a d

- Score: 10.5 / 15

Question 2 :
 Student Answers:
    1) Subtraction (A − B): S4 S3 S2 S1 S0 = 0 1 0 1 1
    2) INC A (A = A + 1):   A0= A B0= 1 | S4 S3 S2 S1 S0 = 0 0 0 0 1
    3) DEC A (A = A − 1):   A0= A B0= 1 | S4 S3 S2 S1 S0 = 0 1 0 1 1
    4) INV A:               A0= A B0= 1 | S4 S3 S2 S1 S0 = 1 0 0 0 0
    5) Carry-out circuit:   (student drawing)Half-adder blocks cascaded, Cin connected to first stage, Cout shown at the end

 Key Answers:
    1) Subtraction (A − B): S4 S3 S2 S1 S0 = 0 1 0 1 1
    2) INC A (A = A + 1):   Solution 1: A0= A B0= 1 | S4 S3 S2 S1 S0 = 0 0 0 0 1
                            Solution 2: A0= A B0= 0 | S4 S3 S2 S1 S0 = 0 0 0 1 1
    3) DEC A (A = A − 1):   A0= A B0= 1 | S4 S3 S2 S1 S0 = 0 1 0 1 1
    4) INV A:               A0= A B0= 1 | S4 S3 S2 S1 S0 = 1 0 0 0 0
    5) Carry-out circuit:   (solution drawing) Full-adder carry-out logic: Cout = (A·B) + (Cin·(A ⊕ B))

- Score: 13.5 / 15


============================================================

Correct Answers + Explanation

============================================================

Question 1 

Q1.1) Equivalent of t2 = A[t0] where base address of A is in $s0
Correct Answer: B.
lw  $t0, 0($s0)
sll $t1, $t0, 2
add $t1, $s0, $t1
lw  $t2, 0($t1)

Explanation:
MIPS uses byte addressing, but arrays of words store 32-bit elements (4 bytes each).
So the effective address must be:
Address = Base(A) + (index × 4)
The shift-left-by-2 performs the ×4, then the base address is added, then lw loads the word.

------------------------------------------------------------

Q1.2) Which instruction uses PC-relative addressing?
Correct Answer: D. beq $t0, $t1, LABEL

Explanation:
Branch instructions compute the destination using an offset relative to PC+4:
Target = (PC + 4) + (imm << 2)
This is the definition of PC-relative addressing.

------------------------------------------------------------

Q1.3) move $t0, $t1  (NOT equivalent)
Correct Answer: D. sub $t0, $zero, $t1

Explanation:
move copies the register value:
t0 ← t1
But sub $t0, $zero, $t1 computes:
t0 ← 0 − t1 = −t1
So it changes the value (negation) and is not equivalent to move.

------------------------------------------------------------

Q1.4) Decode machine instruction 0x01484820
Correct Answer: A. add $t1, $t2, $t3

Explanation:
This is an R-type instruction.
The funct field 0x20 corresponds to ADD in the MIPS instruction set,
so the operation is a register-register addition.

------------------------------------------------------------

Q1.5) Which register is used with one of the J-type instructions?
Correct Answer: B. $ra

Explanation:
jal (jump and link) stores the return address into $ra automatically,
which is how procedure calls are implemented in MIPS.

------------------------------------------------------------

Q1.6) Final value after: lui $t0, 0x1234  (assuming $t0 initially 0)
Correct Answer: A. 0x12340000

Explanation:
lui loads the immediate into the upper 16 bits and clears the lower 16 bits:
t0 = 0x1234 << 16 = 0x12340000

------------------------------------------------------------

Q1.7) If beq at 0x00400020 branches to 0x00400028, what is Label?
Correct Answer: A. 1

Explanation:
PC+4 = 0x00400024
Difference = 0x00400028 − 0x00400024 = 4 bytes
imm << 2 = 4  ⇒ imm = 1

------------------------------------------------------------

Q1.8) Signed overflow in A − B occurs when:
Correct Answer: C. A is positive and B is negative

Explanation:
A − B is implemented as A + (~B + 1).
If B is negative, then (−B) becomes positive.
So the CPU effectively adds two positives, which can exceed the positive signed range.

------------------------------------------------------------

Q1.9) 4-bit multiplicand × 4-bit multiplier (first-version multiplication)
Correct Answer: A. 8-bits ALU

Explanation:
A 4-bit number can be up to 15.
15 × 15 = 225, which needs 8 bits to represent.
So the datapath must support an 8-bit result width.

------------------------------------------------------------

Q1.10) IEEE-754 single precision for −1.5
Correct Answer: D.
10111111110000000000000000000000

Explanation:
−1.5 in binary is −(1.1 × 2^0).
Sign = 1
Exponent = 127 (bias) = 01111111
Fraction = 1000000...
This matches option D.

------------------------------------------------------------

Key Answer Table:
b d d a b a a c a d

============================================================
Question 2 

Q2.1) Subtraction (A − B)
Key: S4 S3 S2 S1 S0 = 0 1 0 1 1

Explanation:
Subtraction uses two’s complement:
A − B = A + (~B) + 1
So the control selects the ADD datapath, inverts B, and sets carry-in to 1.

------------------------------------------------------------

Q2.2) INC A  (A = A + 1)
Key: A0=A, B0=1 | S4 S3 S2 S1 S0 = 0 0 0 1 1

Explanation:
Increment is adding constant 1:
A + 1
So the datapath feeds A normally and enables the +1 behavior through the control signals.

------------------------------------------------------------

Q2.3) DEC A  (A = A − 1)
Key: A0=A, B0=1 | S4 S3 S2 S1 S0 = 0 1 0 1 1

Explanation:
Decrement is:
A − 1
It is commonly implemented using the same subtraction mode configuration.

------------------------------------------------------------

Q2.4) INV A
Key: S4 S3 S2 S1 S0 = 1 1 X X 0

Explanation:
INV A outputs the bitwise inversion of A:
~A
X means “don’t care” lines for this operation.

------------------------------------------------------------

Q2.5) Carry-out circuit for full adder
Key formula:
Cout = (A·B) + (Cin·(A ⊕ B))

Explanation:
Carry-out is generated when A and B are both 1, or when Cin is 1 and exactly one of A/B is 1.
This is the standard carry logic for a full adder.
"""
