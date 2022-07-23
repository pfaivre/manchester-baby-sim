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
            A = b("000")
            B = b("100")
            C = b("010")
            D = b("110")
            E = b("001")
            # F = b("101")
            G = b("011")
            H = b("111")
            I = None
        self.mock_model.Mnemonic = SampleMnemonic

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

    def test_load_asm(self):
        pass

    def test_load_snp(self):
        pass

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
                result = test_func(mock_self, b(input))
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
        pass
