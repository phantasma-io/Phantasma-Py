from datetime import datetime
from typing import Any
from enum import Enum, IntEnum
from .Opcode import Opcode
from .VMType import VMType
from ..Utils import number_to_byte_array


class ScriptBuilder():

    '''
    The ScriptBuilder object implements all the methods needed to build a Phantasma Script string
    which is needed to interact with the Phantasma Blockchain.

    Args:
        None

    Attributes:
        data (str): This is where we store the script string.
        Nexus (dict): Dictionary which contains Phantasma Blockchain contract names.
        nullAddress (str): Phantasma Blockchain NULL address representation.
        _labelLocations (list): Label's location list
        _jumpLocations (list): Jump's location list
    '''

    Nexus = dict(
        GasContractName='gas',
        BlockContractName='block',
        StakeContractName='stake',
        SwapContractName='swap',
        AccountContractName='account',
        ConsensusContractName='consensus',
        GovernanceContractName='governance',
        StorageContractName='storage',
        ValidatorContractName='validator',
        InteropContractName='interop',
        ExchangeContractName='exchange',
        PrivacyContractName='privacy',
        RelayContractName='relay',
        RankingContractName='ranking'
    )

    MAX_REGISTER_COUNT = 32

    data: str = None
    _labelLocations = []
    _jumpLocations = []

    nullAddress = "S1111111111111111111111111111111111"

    def __init__(self) -> None:
        self.data = ""
        self._labelLocations = []
        self._jumpLocations = []

    def BeginScript(self) -> None:
        '''This method initializes an empty script.

        Args:
            None

        Returns:
            None
        '''

        self.data = ""
        self._labelLocations = []
        self._jumpLocations = []

    def GetScript(self) -> str:
        '''This method returns the generated script as string.

        Args:
            None

        Returns:
            getScript (str): end result script.
        '''
        return self.data

    def EndScript(self) -> str:
        '''This method finishes the script and return it as string.

        Args:
            None

        Returns:
            endScript (str): end result script.
        '''
        self.Emit(Opcode.RET)
        return self.data

    def Emit(self, opcode: Opcode, data: Any = None) -> None:
        '''This method emits an opcode with its data.

        Args:
            opcode (Opcode): Blockchain opcode to be emitted.
            data (Any): Data related to the opcode to be emitted.

        Returns:
            None
        '''
        self.AppendByte(opcode)
        if data is not None:
            if isinstance(data, list):
                for d in data:
                    self.Emit(d)
            else:
                self.Emit(data)
        return self

    def EmitPush(self, reg: int) -> None:
        '''This method emits a PUSH opcode.

        Args:
            reg (int): register

        Returns:
            None
        '''
        self.Emit(Opcode.PUSH)
        self.AppendByte(reg)
        return self

    def EmitPop(self, reg: int) -> None:
        '''This method emits a POP opcode.

        Args:
            reg (int): register

        Returns:
            None
        '''
        self.Emit(Opcode.POP)
        self.AppendByte(reg)
        return self

    def EmitExtCall(self, method: str, reg: int = 0) -> None:
        '''This method emits a EXTCALL opcode.

        Args:
            method (str): method to be executed.
            reg (int): register

        Returns:
            None
        '''
        self.EmitLoad(reg, method)
        self.Emit(Opcode.EXTCALL)
        self.AppendByte(reg)
        return self

    def RawString(self, value: str) -> list:
        '''This method converts an string to a list of byte characters.

        Args:
            value (str): string to be converted.

        Returns:
            rawString (list): list of byte chars.
        '''
        data = []
        for c in list(value):
            data.append(ord(c))
        return data

    def EmitLoad(self, reg: int, obj: Any) -> None:
        '''This method loads data to the script depending of the object type
        Supported object types are: str, bool, int, float and datetime.

        Args:
            reg (int): register
            obj (Any): data

        Returns:
            None
        '''

        # String
        typeLoaded = False
        if (isinstance(obj, str)):
            data = self.RawString(obj)
            self.EmitLoadBytes(reg, data, VMType.String)
            typeLoaded = True

        # Boolean
        if (isinstance(obj, bool)):
            data = []
            if obj:
                data.append(1)
            else:
                data.append(0)
            self.EmitLoadBytes(reg, data, VMType.Bool)
            typeLoaded = True

        # Number
        # TODO implement correct bigint binary serialization
        if isinstance(obj, int):
            # self.EmitLoadVarInt(reg, obj) # Incorrect
            data = self.RawString(str(obj))
            self.EmitLoadBytes(reg, data, VMType.String)
            typeLoaded = True

        # Timestamp
        if (isinstance(obj, datetime)):
            data = self.RawString(str(obj))
            self.EmitLoadTimestamp(reg, obj)
            typeLoaded = True

        if not typeLoaded:
            raise Exception("Load type " + str(type(obj)) +
                            " is not supported")

        return self

    def EmitLoadVarInt(self, reg, val):
        """
        Emit a LOAD operation for a variable integer.

        Args:
            reg (int): The register number to load the value into.
            val (int): The integer value to load.

        Returns:
            self: Allows for method chaining.
        """
        bytes_val = number_to_byte_array(val)

        self.Emit(Opcode.LOAD)
        self.AppendByte(reg)
        self.AppendByte(VMType.Number)

        self.AppendByte(len(bytes_val))
        self.EmitBytes(bytes_val)
        return self

    def EmitLoadBytes(self, reg: int, data: bytes = None,
                      typ: VMType = VMType.Bytes) -> None:

        '''This method loads bytes data to the script.

        Args:
            reg (int): register.
            data (bytes): data.
            typ (VMType): data type.

        Returns:
            None
        '''

        if data is None:
            data = []

        if len(data) > 0xffff:
            raise Exception("tried to load too much data")

        self.Emit(Opcode.LOAD)
        self.AppendByte(reg)
        self.AppendByte(typ)
        self.EmitVarInt(len(data))
        self.EmitBytes(data)
        return self

    def EmitLoadEnum(self, reg: int, val: int) -> None:
        '''This method loads enum data to the script.

        Args:
            reg (int): register.
            val (int): data.

        Returns:
            None
        '''

        data = [0, 0, 0, 0]

        for i in range(len(data)):
            data[c] = (val & 0xff)
            val = (val - (val & 0xff)) / 256

        self.EmitLoadBytes(reg, data, VMType.Enum)
        return self

    def EmitLoadTimestamp(self, reg: int, obj: datetime) -> None:
        '''This method loads a datetime data to the script as an UTC timestamp.

        Args:
            reg (int): register.
            obj (datetime): data.

        Returns:
            None
        '''

        num = int(obj.replace(tzinfo=timezone.utc).timestamp())

        a = (num & 0xff000000) >> 24
        b = (num & 0x00ff0000) >> 16
        c = (num & 0x0000ff00) >> 8
        d = num & 0x000000ff

        data = [d, c, b, a]
        self.EmitLoadBytes(reg, data, VMType.Timestamp)
        return self

    def EmitMove(self, src_reg: int, dst_reg: int) -> None:
        '''This method emits a MOVE opcode.

        Args:
            src_reg (int): source register.
            dst_reg (int): destination register.

        Returns:
            None
        '''

        self.Emit(Opcode.MOVE)
        self.AppendByte(src_reg)
        self.AppendByte(dst_reg)
        return self

    def EmitCopy(self, src_reg: int, dst_reg: int) -> None:
        '''This method emits a COPY opcode.

        Args:
            src_reg (int): source register.
            dst_reg (int): destination register.

        Returns:
            None
        '''

        self.Emit(Opcode.COPY)
        self.AppendByte(src_reg)
        self.AppendByte(dst_reg)
        return self

    def EmitLabel(self, label: str) -> None:
        '''This method loads a label into the script.

        Args:
            label (str): label data.

        Returns:
            None
        '''

        self.Emit(Opcode.NOP)
        self._labelLocations[label] = len(self.data)
        return self

    def EmitJump(self, opcode: Opcode, label: str, reg: int = 0) -> None:
        '''This method emits a JUMP opcode.

        Args:
            opcode (Opcode): jump opcode to add: Opcode.JMP, Opcode.JMPIF or Opcode.JMPNOT
            label (str): label to jump.
            reg (int): register.

        Returns:
            None
        '''

        if ((opcode == Opcode.JMP) or (
                opcode == Opcode.JMPIF) or (opcode == Opcode.JMPNOT)):
            self.Emit(opcode)
        else:
            raise Exception("Invalid jump opcode: " + str(opcode))

        if (opcode != Opcode.JMP):
            self.AppendByte(reg)

        ofs = len(self.data)
        self.AppendUshort(0)
        self._jumpLocations[ofs] = label
        return self

    def EmitCall(self, label: str, regCount: int) -> None:
        '''This method emits a CALL opcode.

        Args:
            label (str): label to call.
            regCount (int): register counter.

        Returns:
            None
        '''

        if ((regCount < 1) or (regCount > MAX_REGISTER_COUNT)):
            raise Exception("Invalid number of registers")

        ofs = (len(self.data)) + 2
        self.Emit(Opcode.CALL)
        self.AppendUshort(0)
        self._jumpLocations[ofs] = label
        return self

    def EmitConditionalJump(
            self,
            opcode: Opcode,
            src_reg: int,
            label: str) -> None:
        '''This method emits a conditional JUMP opcode.

        Args:
            opcode (Opcode): jump opcode to add: only Opcode.JMPIF and Opcode.JMPNOT are valid.
            label (str): label to jump.
            src_reg (int): source register.

        Returns:
            None
        '''

        if ((opcode != Opcode.JMPIF) and (
                opcode != Opcode.JMPNOT)):
            raise Exception("Opcode is not a conditional jump: " + str(opcode))

        ofs = (len(self.data)) + 2
        self.Emit(opcode)
        self.AppendUshort(0)
        self._jumpLocations[ofs] = label
        return self

    def InsertMethodArgs(self, args: list) -> None:
        '''This loads method arguments into the script.

        Args:
            args (list): list of arguments.

        Returns:
            None
        '''

        temp_reg = 0
        for arg in reversed(args):
            self.EmitLoad(temp_reg, arg)
            self.EmitPush(temp_reg)

    def CallInterop(self, method: str, args: list) -> None:
        '''This method loads an external method and its arguments into the script.

        Args:
            method (str): method to be executed.
            args (list): list of arguments.

        Returns:
            None
        '''

        self.InsertMethodArgs(args)

        dest_reg = 0
        self.EmitLoad(dest_reg, method)
        self.Emit(Opcode.EXTCALL, dest_reg)
        return self

    def CallContract(self, contractName: str, method: str, args: list) -> None:
        '''This method adds a contract method call with its arguments into the script.

        Args:
            contractName (str): contract name to be executed.
            method (str): method to be executed.
            args (list): list of arguments.

        Returns:
            None
        '''

        self.InsertMethodArgs(args)

        temp_reg = 0
        self.EmitLoad(temp_reg, method)
        self.EmitPush(temp_reg)

        src_reg = 0
        dest_reg = 1
        self.EmitLoad(src_reg, contractName)
        self.Emit(Opcode.CTX, [src_reg, dest_reg])
        self.Emit(Opcode.SWITCH, [dest_reg])
        return self

    def EmitVarString(self, text: str) -> None:
        '''This method loads a str variable into the script.

        Args:
            text (str): string data.

        Returns:
            None
        '''

        data = self.RawString(text)
        self.EmitVarInt(len(data))
        self.EmitBytes(data)
        return self

    def EmitVarInt(self, value: int) -> None:
        '''This method loads a int variable into the script.

        Args:
            value (int): int data.

        Returns:
            None
        '''

        if value < 0:
            raise Exception("Negative value invalid")
        if (value < 0xfd):
            self.AppendByte(value)
        elif (value <= 0xffff):
            B = (value & 0x0000ff00) >> 8
            A = value & 0x000000ff
            self.AppendByte(0xfd)
            self.AppendByte(A)
            self.AppendByte(B)
        elif (value <= 0xffffffff):
            C = (value & 0x00ff0000) >> 16
            B = (value & 0x0000ff00) >> 8
            A = value & 0x000000ff
            self.AppendByte(0xfe)
            self.AppendByte(A)
            self.AppendByte(B)
            self.AppendByte(C)
        else:
            D = (value & 0xff000000) >> 24
            C = (value & 0x00ff0000) >> 16
            B = (value & 0x0000ff00) >> 8
            A = value & 0x000000ff
            self.AppendByte(0xff)
            self.AppendByte(A)
            self.AppendByte(B)
            self.AppendByte(C)
            self.AppendByte(D)
        return self

    def EmitBytes(self, data: bytes) -> None:
        '''This method loads a bytes variable into the script.

        Args:
            data (bytes): bytes data.

        Returns:
            None
        '''

        for i in data:
            self.AppendByte(i)

    def ByteToHex(self, data: int) -> str:
        '''This method converts a byte into an str hex representation.

        Args:
            data (int): byte data to be converted to hex.

        Returns:
            byteToHex (str): str hex representatiom of the byte.
        '''

        res = format(data, 'x').upper()
        if len(res) == 1:
            res = "0" + res
        return res

    def AppendByte(self, data: int) -> None:
        '''This method loads a byte variable into the script.

        Args:
            data (int): int data.

        Returns:
            None
        '''

        self.data = self.data + self.ByteToHex(data)

    def AppendUshort(self, ushort: int) -> None:
        '''This method loads a unsigned short int variable into the script.

        Args:
            data (int): unsigned short int data.

        Returns:
            None
        '''

        self.data = self.data + \
            (self.ByteToHex(ushort & 0xff)) + (this.byteToHex((ushort >> 8) & 0xff))

    def AppendHexEncoded(self, data: str) -> None:
        '''This method loads an Hex string variable into the script.

        Args:
            data (str): Hex data to be loaded.

        Returns:
            None
        '''

        self.data = self.data + data
        return self

    # ScriptBuilderExtensions
    def AllowGas(
            self,
            frm: str,
            to: str,
            gasPrice: int,
            gasLimit: int) -> None:
        return self.CallContract(
            self.Nexus["GasContractName"], "AllowGas", [
                frm, to, gasPrice, gasLimit])
        '''This method is a wrapper that invokes the method AllowGas from the gas contract.

        Args:
            frm (str): Phantasma wallet address where gas fees are going to be spent.
            to (str): Phantasma wallet address where gas fees are going to be sent (NULL Address).
            gasPrice (int): Max gas price to used.
            gasLimit (int): Gas limit to be used.

        Returns:
            None
        '''

    def SpendGas(self, address: str) -> None:
        return self.CallContract(
            self.Nexus["GasContractName"], "SpendGas", [address])
        '''This method is a wrapper that invokes the method SpendGas from the gas contract.

        Args:
            address (str): Phantasma wallet address where gas fees are going to be spent.

        Returns:
            None
        '''
