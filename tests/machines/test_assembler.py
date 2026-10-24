import tempfile
from enum import Enum
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, mock_open, patch

from src.core.bitarray import b
from src.core.store import Store
from src.machines.assembler import Assembler, AssemblerError
from src.machines.ssemmodel import SsemModel


class TestAssembler(TestCase):

    def setUp(self):
        self.mock_model = MagicMock()
        self.mock_model.word_length = 32
        self.mock_model.word_count = 3
        self.mock_model.opcode_start = 13
        self.mock_model.opcode_length = 3
        self.mock_model.address_start = 0
        self.mock_model.address_length = 5
        class SampleMnemonic(Enum):
            A = 0
            B = 1
            C = 2
            D = 3
            E = 4
            # F = 5
            G = 6
            H = 7
            I = None
        self.mock_model.Mnemonic = SampleMnemonic

    def _temp_file(self, content: str, suffix: str = ".asm") -> Path:
        """Write the given content to a temporary file and return its path"""
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        path = Path(tmpdir.name) / f"program{suffix}"
        path.write_text(content)
        return path

    def _real_assembler(self) -> Assembler:
        """Assembler operating on the real SSEM model"""
        return Assembler(model=SsemModel())

    def _real_store(self) -> Store:
        return Store(SsemModel.word_length, SsemModel.word_count)

    def test_load_file(self):
        # Test case: asm file
        # Arrange
        mock_self = MagicMock(spec=Assembler)
        mock_store = MagicMock(spec=Store)
        mock_self._guess_file_format.return_value = "asm"
        # Act
        Assembler.load_file(mock_self, Path("some_path"), mock_store)
        # Assert
        mock_self.load_asm.assert_called_once_with(Path("some_path"), mock_store)
        mock_self.load_snp.assert_not_called()

        # Test case: snp file
        # Arrange
        mock_self = MagicMock(spec=Assembler)
        mock_store = MagicMock(spec=Store)
        mock_self._guess_file_format.return_value = "snp"
        # Act
        Assembler.load_file(mock_self, Path("some_path"), mock_store)
        # Assert
        mock_self.load_asm.assert_not_called()
        mock_self.load_snp.assert_called_once_with(Path("some_path"), mock_store)

        # Test case: unknown format
        # Arrange
        mock_self = MagicMock(spec=Assembler)
        mock_store = MagicMock(spec=Store)
        mock_self._guess_file_format.return_value = None
        # Act
        with self.assertRaises(AssemblerError):
            Assembler.load_file(mock_self, Path("some_path"), mock_store)

    def test_load_file_from_disk(self):
        """load_file guesses the format from the content and dispatches accordingly"""
        assembler = self._real_assembler()

        # Test case: asm file
        store = self._real_store()
        assembler.load_file(self._temp_file("00 LDN 20\n01 STP\n"), store)
        self.assertEqual(store[0], b("00101000000000100000000000000000"), "00 LDN 20")

        # Test case: snp file
        store = self._real_store()
        assembler.load_file(self._temp_file("0000: 11111000000000100000000000000000\n", suffix=".snp"), store)
        self.assertEqual(store[0], b("11111000000000100000000000000000"))

    def test_load_file_not_found(self):
        assembler = self._real_assembler()
        with self.assertRaises(AssemblerError):
            assembler.load_file(Path("this_file_does_not_exist.asm"), self._real_store())

    def test_load_file_directory(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        assembler = self._real_assembler()
        with self.assertRaises(AssemblerError):
            assembler.load_file(Path(tmpdir.name), self._real_store())

    def test_load_file_unknown_format(self):
        assembler = self._real_assembler()
        with self.assertRaises(AssemblerError):
            assembler.load_file(self._temp_file("foo bar\n"), self._real_store())

    def test_load_asm(self):
        """A valid assembly program is written word by word into the store"""
        program = "\n".join([
            "; Addition program",
            "00 LDN 04    ; A = -X",
            "01 SUB 05    ; A = A - Y",
            "02 STO 06    ; R = A",
            "03 STP",
            "",
            "04 NUM 3",
            "05 NUM 4",
            "06 NUM -5",
        ])
        assembler = self._real_assembler()
        store = self._real_store()
        store[10] = b("11111111111111111111111111111111")  # Pre-existing content

        assembler.load_asm(self._temp_file(program), store)

        # Instructions: 5-bit operand at bit 0, 3-bit opcode at bit 13
        self.assertEqual(store[0], b("00100000000000100000000000000000"), "00 LDN 04")
        self.assertEqual(store[1], b("10100000000000010000000000000000"), "01 SUB 05")
        self.assertEqual(store[2], b("01100000000001100000000000000000"), "02 STO 06")
        self.assertEqual(store[3], b("00000000000001110000000000000000"), "03 STP")

        # Numbers, written as two's complement
        self.assertEqual(store[4], b("11000000000000000000000000000000"), "04 NUM 3")
        self.assertEqual(store[5], b("00100000000000000000000000000000"), "05 NUM 4")
        self.assertEqual(store[6], b("11011111111111111111111111111111"), "06 NUM -5")

        # Lines absent from the program are cleared
        self.assertEqual(store[10], b("00000000000000000000000000000000"), "Cleared")

    def test_load_asm_errors(self):
        test_suite = {
            "address not numeric":      "zero LDN 20\n",
            "address out of sequence":  "01 LDN 20\n",
            "invalid mnemonic":         "00 LOADX 20\n",
            "missing mnemonic":         "00\n",
            "missing data":             "00 LDN\n",
            "data not numeric":         "00 LDN twenty\n",
            "data out of address range": "00 LDN 32\n",
            "number too large":         "00 NUM 99999999999\n",
            "too many words":           "".join(f"{i:02d} STP\n" for i in range(33)),
        }

        assembler = self._real_assembler()
        for name, program in test_suite.items():
            with self.subTest(name):
                store = self._real_store()
                with self.assertRaises(AssemblerError):
                    assembler.load_asm(self._temp_file(program), store)

    def test_load_snp(self):
        """A valid binary dump is written word by word into the store"""
        program = "\n".join([
            "; A comment",
            "",
            "0000: 00000000000000000000000000000000",
            "0001: 11111000000000100000000000000000 ; Some comment",
            "0002: 01111000000001100000000000000000",
        ])
        assembler = self._real_assembler()
        store = self._real_store()
        store[5] = b("11111111111111111111111111111111")  # Pre-existing content

        assembler.load_snp(self._temp_file(program, suffix=".snp"), store)

        self.assertEqual(store[0], b("00000000000000000000000000000000"))
        self.assertEqual(store[1], b("11111000000000100000000000000000"))
        self.assertEqual(store[2], b("01111000000001100000000000000000"))

        # Lines absent from the dump are cleared
        self.assertEqual(store[5], b("00000000000000000000000000000000"), "Cleared")

    def test_load_snp_errors(self):
        test_suite = {
            "address out of sequence": "0005: " + "0" * 32 + "\n",
            "missing word":            "0000\n",
            "word too long":           "0000: " + "0" * 33 + "\n",
            "word too short":          "0000: 0101\n",
            "too many words":          "".join(f"{i:04d}: " + "0" * 32 + "\n" for i in range(33)),
        }

        assembler = self._real_assembler()
        for name, program in test_suite.items():
            with self.subTest(name):
                store = self._real_store()
                with self.assertRaises(AssemblerError):
                    assembler.load_snp(self._temp_file(program, suffix=".snp"), store)

    def test__guess_file_format(self):
        mock_self = MagicMock(spec=Assembler)

        test_func = Assembler._guess_file_format

        test_suite = {
            """; Some comment

00 NUM 1    ;Incremental Value
01 LDN 31   ;Load negative of counter
02 SUB 0    ;"Increment" our counter
""": "asm",

            """01 CMP
""": "asm",

            """999999 LOADX
""": "asm",

            """; Some comment

0000: 00000000000000000000000000000000
0001: 11111000000000100000000000000000 ; Some comment
0002: 01111000000001100000000000000000
""": "snp",

            """; Some comment

foo bar
""": None,

            """""": None
        }

        for input, expected_output in test_suite.items():
            with patch("builtins.open", mock_open(read_data=input)) as mock_file:
                result = test_func(mock_self, Path("some_file"))
                self.assertEqual(result, expected_output)

    def test_decode_instruction(self):
        mock_self = MagicMock(spec=Assembler)
        mock_self.model = self.mock_model

        test_func = Assembler.decode_instruction

        test_suite = {
            # Testing function code
            "11111000000000000000000000000000": (self.mock_model.Mnemonic.A, 31),
            "11111000000001000000000000000000": (self.mock_model.Mnemonic.B, 31),
            "11111000000000100000000000000000": (self.mock_model.Mnemonic.C, 31),
            "11111000000001100000000000000000": (self.mock_model.Mnemonic.D, 31),
            "11111000000000010000000000000000": (self.mock_model.Mnemonic.E, 31),
            "11111000000001010000000000000000": AssemblerError,
            "11111000000000110000000000000000": (self.mock_model.Mnemonic.G, 31),
            "11111000000001110000000000000000": (self.mock_model.Mnemonic.H, 31),
            "11111111111111111111111111111111": (self.mock_model.Mnemonic.H, 31),

            # Testing operand
            "00000000000000000000000000000000": (self.mock_model.Mnemonic.A, 0),
            "10000000000000000000000000000000": (self.mock_model.Mnemonic.A, 1),
            "01000000000000000000000000000000": (self.mock_model.Mnemonic.A, 2),
            "00100000000000000000000000000000": (self.mock_model.Mnemonic.A, 4),
            "00010000000000000000000000000000": (self.mock_model.Mnemonic.A, 8),
            "00001000000000000000000000000000": (self.mock_model.Mnemonic.A, 16),
            "00000100000000000000000000000000": (self.mock_model.Mnemonic.A, 0),
            "00000111111110001111111111111111": (self.mock_model.Mnemonic.A, 0),

            "0000011111111000": (self.mock_model.Mnemonic.A, 0),
            "000001111111100":  AssemblerError,
            "0":                AssemblerError,
        }

        for input, expected_output in test_suite.items():
            if expected_output == AssemblerError:
                with self.assertRaises(expected_output):
                    test_func(mock_self, b(input))

            else:
                result = test_func(mock_self, b(input))
                self.assertEqual(result, expected_output)

    def test_disassemble(self):
        """Disassembly is not implemented yet"""
        with self.assertRaises(NotImplementedError):
            self._real_assembler().disassemble(self._real_store())
