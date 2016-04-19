import unittest
from python_toolkit.arrayQuery import single, NoValueExc
from vhdl_toolkit.hdlObjects.typeDefs import INT, UINT, PINT
from vhdl_toolkit.hdlObjects.typeShortcuts import hInt
from vhdl_toolkit.hdlObjects.operator import Operator
from vhdl_toolkit.hdlObjects.operatorDefs import AllOps
from vhdl_toolkit.hdlObjects.expr import ExprComparator
from vhdl_toolkit.synthetisator.interfaceLevel.unitUtils import synthesised
from vhdl_toolkit.synthetisator.interfaceLevel.unitFromHdl import UnitFromHdl
from vhdl_toolkit.synthetisator.param import Param
from vhdl_toolkit.synthetisator.rtlLevel.signal import SignalNode
from vhdl_toolkit.interfaces.amba import AxiLite
from vhdl_toolkit.interfaces.std import Ap_clk, \
    Ap_rst_n, BramPort, Ap_vld
from vhdl_toolkit.tests.synthetisator.interfaceLevel.baseSynthetisatorTC import BaseSynthetisatorTC

ILVL_VHDL = '../../../samples/iLvl/vhdl/'


class VhdlCodesignTC(BaseSynthetisatorTC):

    def testTypeInstances(self):
        from vhdl_toolkit.hdlObjects import typeDefs
        from vhdl_toolkit.hdlContext import BaseVhdlContext
        self.assertIs(INT, typeDefs.INT)
        ctx = BaseVhdlContext.getBaseCtx()
        self.assertIs(ctx['integer'], INT)

    def test_bramIntfDiscovered(self):
        from vhdl_toolkit.samples.iLvl.bram import Bram
        bram = Bram()
        bram._loadAll()
        self.assertTrue(hasattr(bram, 'a'), 'port a found')
        self.assertTrue(hasattr(bram, 'b'), 'port b found')
        bp = BramPort()
        bp._loadDeclarations()
        for p in [bram.a, bram.b]:
            for i in bp._interfaces:
                propName = i._name
                self.assertTrue(hasattr(p, propName), 'bram port instance has ' + propName)
                subPort = getattr(p, propName)
                self.assertTrue(subPort in p._interfaces,
                                 "subport %s is in interface._interfaces" % (propName))

    def test_axiStreamExtraction(self):
        class AxiStreamSampleEnt(UnitFromHdl):
            _hdlSources = ILVL_VHDL + "axiStreamSampleEnt.vhd"
        # (intfClasses=[AxiStream_withUserAndStrb, AxiStream, AxiStream_withUserAndNoStrb,
        #  AxiStream_withoutSTRB])
        u = AxiStreamSampleEnt()
        u._loadAll()
        # [TODO] sometimes resolves as 'RX0_ETH_T' it is not deterministic, need better example
        self.assertTrue(hasattr(u, "RX0_ETH"))
        self.assertTrue(hasattr(u, "RX0_CTL"))
        self.assertTrue(hasattr(u, "TX0_ETH"))
        self.assertTrue(hasattr(u, "TX0_CTL"))
        
        self.assertIs(u.RX0_ETH.DATA_WIDTH,  u.C_DATA_WIDTH)
        self.assertEqual(u.RX0_ETH.data._dtype.getBitCnt(), u.C_DATA_WIDTH.get().val)
        self.assertIs(u.RX0_ETH.USER_WIDTH,  u.C_USER_WIDTH)
        self.assertEqual(u.RX0_ETH.user._dtype.getBitCnt(), u.C_USER_WIDTH.get().val)
        
        

    def test_genericValues(self):
        class GenericValuesSample(UnitFromHdl):
            _hdlSources = ILVL_VHDL + "genericValuesSample.vhd"
        u = GenericValuesSample()
        self.assertEqual(u.C_BASEADDR._val.val, (2 ** 32) - 1)
        self.assertEqual(u.C_FAMILY._val.val, 'zynq')

    def test_ClkAndRstExtraction(self):
        class ClkRstEnt(UnitFromHdl):
            _hdlSources = ILVL_VHDL + "clkRstEnt.vhd"
        u = ClkRstEnt(intfClasses=[Ap_clk, Ap_rst_n])
        u._loadAll()
        
        self.assertIsInstance(u.ap_rst_n, Ap_rst_n)
        self.assertIsInstance(u.ap_clk, Ap_clk)

    def test_positiveAndNatural(self):
        class PositiveAndNatural(UnitFromHdl):
            _hdlSources = ILVL_VHDL + "positiveAndNatural.vhd"
        u = PositiveAndNatural()
        natG = single(u._entity.generics, lambda x: x.name == "nat")
        posG = single(u._entity.generics, lambda x: x.name == "pos")
        intG = single(u._entity.generics, lambda x: x.name == "int")
        self.assertEqual(natG.dtype, UINT)
        self.assertEqual(posG.dtype, PINT)
        self.assertEqual(intG.dtype, INT)

    def test_axiLiteSlave2(self):
        class AxiLiteSlave2(UnitFromHdl):
            _hdlSources = ILVL_VHDL + "axiLite_basic_slave2.vhd"
        u = AxiLiteSlave2(intfClasses=[AxiLite, Ap_clk, Ap_rst_n])
        u._loadAll()
        
        self.assertTrue(hasattr(u, "ap_clk"))
        self.assertTrue(hasattr(u, "ap_rst_n"))
        self.assertTrue(hasattr(u, "axilite"))

    def test_withPartialyInvalidInterfaceNames(self):
        class EntityWithPartialyInvalidIntf(UnitFromHdl):
            _hdlSources = ILVL_VHDL + "entityWithPartialyInvalidIntf.vhd"

        u = EntityWithPartialyInvalidIntf()
        u._loadAll()

        self.assertEqual(u.descrBM_w_wr_addr_V_123._parent, u)
        self.assertEqual(u.descrBM_w_wr_din_V._parent, u)
        self.assertEqual(u.descrBM_w_wr_dout_V._parent, u)
        self.assertEqual(u.descrBM_w_wr_en._parent, u)
        self.assertEqual(u.descrBM_w_wr_we._parent, u)

    def test_simplePortDirections(self):
        from vhdl_toolkit.samples.iLvl.bram import Bram
        bram = Bram(intfClasses=[BramPort])
        bram._loadAll()
        
        self.assertIsS(bram.a)
        self.assertIsS(bram.a.clk)
        self.assertIsS(bram.a.addr)
        self.assertIsS(bram.a.din)
        self.assertIsS(bram.a.dout)
        self.assertIsS(bram.a.we)

        self.assertIsS(bram.b)
        self.assertIsS(bram.b.clk)
        self.assertIsS(bram.b.addr)
        self.assertIsS(bram.b.din)
        self.assertIsS(bram.b.dout)
        self.assertIsS(bram.b.we)

    def test_axiPortDirections(self):
        from vhdl_toolkit.samples.iLvl.axi_basic import AxiLiteBasicSlave
        a = AxiLiteBasicSlave()  # (intfClasses=[AxiLite_xil, Ap_clk, Ap_rst_n])
        a._loadAll()
        
        self.assertIsS(a.S_AXI)
        self.assertIsS(a.S_AXI.ar)
        self.assertIsS(a.S_AXI.aw)
        self.assertIsS(a.S_AXI.r)
        self.assertIsS(a.S_AXI.w)
        self.assertIsS(a.S_AXI.b)

        self.assertIsS(a.S_AXI.b.resp)
        self.assertIsS(a.S_AXI.b.valid)
        self.assertIsS(a.S_AXI.b.ready)

    def test_axiParamsIn_Entity(self):
        from vhdl_toolkit.samples.iLvl.axiLiteSlaveContainer import AxiLiteSlaveContainer
        u = AxiLiteSlaveContainer()
        u._loadAll()
        u = synthesised(u)

        aw = None
        dw = None
        try:
            aw = single(u._entity.generics, lambda x: x.name == "ADDR_WIDTH")
        except NoValueExc:
            pass

        try:
            dw = single(u._entity.generics, lambda x: x.name == "DATA_WIDTH")
        except NoValueExc:
            pass
        
        self.assertTrue(aw is not None)
        self.assertTrue(dw is not None)

    def test_axiParams(self):
        from vhdl_toolkit.samples.iLvl.axiLiteSlaveContainer import AxiLiteSlaveContainer
        u = AxiLiteSlaveContainer()
        u._loadAll()
        AW_p = u.axi.ADDR_WIDTH
        DW_p = u.axi.DATA_WIDTH
        
        
        AW = AW_p.get()
        self.assertEqual(AW, hInt(13))
        DW = DW_p.get()
        self.assertEqual(DW, hInt(14))
        
        # self.assertEqual(u.slv.C_S_AXI_ADDR_WIDTH.get(), AW)
        # self.assertEqual(u.slv.C_S_AXI_DATA_WIDTH.get(), DW)
        #
        # self.assertEqual(u.slv.S_AXI.ADDR_WIDTH.get(), AW)
        # self.assertEqual(u.slv.S_AXI.ADDR_WIDTH.get(), DW)
        
        self.assertEqual(u.axi.ADDR_WIDTH.get(), hInt(13))
        self.assertEqual(u.axi.ar.ADDR_WIDTH.get(), hInt(13))
        self.assertEqual(u.axi.ar.addr._dtype.getBitCnt(), 13)

        self.assertEqual(u.axi.ADDR_WIDTH.get(), AW)
        self.assertEqual(u.axi.ar.ADDR_WIDTH.get(), AW)
        self.assertEqual(u.axi.ar.addr._dtype.getBitCnt(), AW.val)
        # [TODO] width of parametrized interfaces from VHDL should be Param with expr

        self.assertEqual(u.axi.w.strb._dtype.getBitCnt(), DW.val // 8)
        self.assertEqual(u.slv.C_S_AXI_ADDR_WIDTH.get().get(), AW)
        self.assertEqual(u.slv.C_S_AXI_DATA_WIDTH.get().get(), DW)

        self.assertEqual(u.slv.S_AXI.ar.addr._dtype.getBitCnt(), AW.val)

    def test_paramsExtractionSimple(self):
        class Ap_vldWithParam(UnitFromHdl):
            _hdlSources = ILVL_VHDL + "ap_vldWithParam.vhd"
        u = Ap_vldWithParam()
        u._loadAll()
        
        self.assertIsInstance(u.data, Ap_vld)
        # print("Ap_vldWithParam.data_width %d" % id(Ap_vldWithParam.data_width))
        # print("Ap_vldWithParam.data.DATA_WIDTH %d" % id(Ap_vldWithParam.data.DATA_WIDTH))
        # print("u.data_width %d" % id(u.data_width))
        # print("u.data.DATA_WIDTH %d" % id(u.data.DATA_WIDTH))
        self.assertEqual(u.DATA_WIDTH, u.data.DATA_WIDTH)
        self.assertEqual(u.data.DATA_WIDTH.get().val, 13)

        self.assertEqual(u.data.data._dtype.getBitCnt(), 13)

    def test_compatibleExpression(self):

        def mkExpr0(val):
            return SignalNode.resForOp(Operator(AllOps.DOWNTO, [val, hInt(0)]))

        def mkExpr0WithMinusOne(val):
            val = SignalNode.resForOp(Operator(AllOps.MINUS, [val, hInt(1)]))
            return SignalNode.resForOp(Operator(AllOps.DOWNTO, [val, hInt(0)]))

        sig_a = Param(0)
        sig_b = Param(1)

        a = mkExpr0(sig_a)
        b = mkExpr0(sig_b)
        m = ExprComparator.isSimilar(a, b, sig_a)
        self.assertTrue(m[0])
        self.assertEqual(m[1], sig_b)
        r = list(ExprComparator.findExprDiffInParam(a, b))[0]
        self.assertSequenceEqual(r, (sig_a, sig_b))

        sig_a = Param(9)
        sig_b = Param(1)

        a = mkExpr0WithMinusOne(sig_a)
        b = mkExpr0WithMinusOne(sig_b)
        m = ExprComparator.isSimilar(a, b, sig_a)
        self.assertTrue(m[0])
        self.assertEqual(m[1], sig_b)
        r = list(ExprComparator.findExprDiffInParam(a, b))[0]
        self.assertSequenceEqual(r, (sig_a, sig_b))

        v = a.staticEval()
        self.assertSequenceEqual(v.val, [hInt(0), hInt(8)])

        sig_a.set(hInt(11))
        v = a.staticEval()
        self.assertSequenceEqual(v.val, [hInt(0), hInt(10)])

        v = b.staticEval()
        self.assertSequenceEqual(v.val, [hInt(0), hInt(0)])

        sig_b.set(hInt(2))
        v = b.staticEval()
        self.assertSequenceEqual(v.val, [hInt(0), hInt(1)])


    def test_largeBitStrings(self):
        class BitStringValuesEnt(UnitFromHdl):  
            _hdlSources = ILVL_VHDL + "bitStringValuesEnt.vhd"
        u = BitStringValuesEnt()
        u._loadAll()
        
        self.assertEqual(u.C_32b0.defaultVal.val, 0)
        self.assertEqual(u.C_16b1.defaultVal.val, (1 << 16) - 1)
        self.assertEqual(u.C_32b1.defaultVal.val, (1 << 32) - 1)
        self.assertEqual(u.C_128b1.defaultVal.val, (1 << 128) - 1)
        # print(u._entity)
    
    def test_interfaceArrayExtraction(self):
        class InterfaceArraySample(UnitFromHdl):
            _hdlSources = ILVL_VHDL + "interfaceArraySample.vhd"        
        u = InterfaceArraySample(intfClasses=[Ap_vld])
        u._loadAll()
        
        width = 3
        self.assertEqual(u.a._multipliedBy, hInt(width))
        self.assertEqual(u.a.DATA_WIDTH.get().val, 8)
        self.assertEqual(u.a.data._dtype.getBitCnt(), 8 * width)
        self.assertEqual(u.a.vld._dtype.getBitCnt(), width)

        self.assertEqual(u.b._multipliedBy, hInt(width))
        self.assertEqual(u.b.DATA_WIDTH.get().val, 8)
        self.assertEqual(u.b.data._dtype.getBitCnt(), 8 * width)
        self.assertEqual(u.b.vld._dtype.getBitCnt(), width)
    
    def test_SizeExpressions(self):
        class SizeExpressionsSample(UnitFromHdl):
            _hdlSources = ILVL_VHDL + "sizeExpressions.vhd"        
        u = SizeExpressionsSample()
        u._loadAll()
        
        A = u.param_A.get()
        B = u.param_B.get()
        self.assertEqual(u.portA._dtype.getBitCnt(), A.val)
        self.assertEqual(u.portB._dtype.getBitCnt(), A.val)
        self.assertEqual(u.portC._dtype.getBitCnt(), A.val // 8)
        self.assertEqual(u.portD._dtype.getBitCnt(), (A.val // 8) * 13)
        self.assertEqual(u.portE._dtype.getBitCnt(), B.val * (A.val // 8))
        self.assertEqual(u.portF._dtype.getBitCnt(), B.val * A.val)
        self.assertEqual(u.portG._dtype.getBitCnt(), B.val * (A.val - 4))
        
    
if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTest(VhdlCodesignTC('test_axiStreamExtraction'))
    #suite.addTest(unittest.makeSuite(VhdlCodesignTC))
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
