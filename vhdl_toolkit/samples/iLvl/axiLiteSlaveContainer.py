from vhdl_toolkit.synthetisator.interfaceLevel.unit import Unit
from vhdl_toolkit.interfaces.amba import  AxiLite
from vhdl_toolkit.samples.iLvl.axi_basic import AxiLiteBasicSlave

from vhdl_toolkit.synthetisator.shortcuts import synthetizeCls
from vhdl_toolkit.synthetisator.param import Param
from vhdl_toolkit.synthetisator.interfaceLevel.interface import connect


class AxiLiteSlaveContainer(Unit):
    def _config(self):
        self.ADDR_WIDTH = Param(13)
        self.DATA_WIDTH = Param(14)
        
    def _declr(self):
        self.slv = AxiLiteBasicSlave()
        self.axi = AxiLite(isExtern=True)
        self._shareAllParams()
        self.slv.C_S_AXI_ADDR_WIDTH.set(self.ADDR_WIDTH)
        self.slv.C_S_AXI_DATA_WIDTH.set(self.DATA_WIDTH)

    def _impl(self):
        connect(self.axi, self.slv.S_AXI)
    
if __name__ == "__main__":
    u = AxiLiteSlaveContainer()
    u._loadDeclarations()
    u._loadImplementations()
    
    print(u.ADDR_WIDTH.get())
    #print(u.slv.C_S_AXI_ADDR_WIDTH.get())
    print(u.slv.S_AXI.ADDR_WIDTH.get())
    print(u.slv.S_AXI.ar.ADDR_WIDTH.get())
    print(u.slv.S_AXI.ar.addr._dtype.getBitCnt())
    
    print(synthetizeCls(AxiLiteSlaveContainer, "axiLSlvCont"))
