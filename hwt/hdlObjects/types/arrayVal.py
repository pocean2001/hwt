from hwt.hdlObjects.operator import Operator
from hwt.hdlObjects.operatorDefs import AllOps
from hwt.hdlObjects.types.defs import BOOL, INT
from hwt.hdlObjects.types.slice import Slice
from hwt.hdlObjects.types.typeCast import toHVal
from hwt.hdlObjects.value import Value
from hwt.synthesizer.param import evalParam
from hwt.synthesizer.rtlLevel.mainBases import RtlSignalBase


class ArrayVal(Value):
    """
    Class of value of array
    """

    @classmethod
    def fromPy(cls, val, typeObj):
        size = evalParam(typeObj.size)
        if isinstance(size, Value):
            size = int(size)

        elements = {}
        if val is None:
            pass
        elif isinstance(val, dict):
            for k, v in val:
                if not isinstance(k, int):
                    k = int(k)
                elements[k] = v
        else:
            for k, v in enumerate(val):
                if isinstance(v, RtlSignalBase):  # is signal
                    assert v._dtype == typeObj.elmType
                    e = v
                else:
                    e = typeObj.elmType.fromPy(v)
                elements[k] = e

        return cls(elements, typeObj, int(bool(val)))

    def __hash__(self):
        return hash((self._dtype, self.updateTime))
        # return hash((self._dtype, self.val, self.vldMask, self.updateTime))

    def _isFullVld(self):
        return self.vldMask == 1

    def _getitem__val(self, key):
        """
        :atention: this will clone item from array, iterate over .val if you need to modify items
        """
        try:
            kv = key.val
            if not key._isFullVld():
                raise KeyError()
            else:
                if kv >= self._dtype.size:
                    raise IndexError()

            v = self.val[kv]
            return v.clone()
        except KeyError:
            return self._dtype.elmType.fromPy(None)

    def __getitem__(self, key):
        iamVal = isinstance(self, Value)
        key = toHVal(key)
        isSLICE = isinstance(key, Slice.getValueCls())

        if isSLICE:
            raise NotImplementedError()
        elif isinstance(key, RtlSignalBase):
            key = key._convert(INT)
        elif isinstance(key, Value):
            pass
        else:
            raise NotImplementedError("Index operation not implemented for index %s"
                                      % (repr(key)))

        if iamVal and isinstance(key, Value):
            return self._getitem__val(key)

        return Operator.withRes(AllOps.INDEX, [self, key], self._dtype.elmType)

    def _setitem__val(self, index, value):
        self.updateTime = max(index.updateTime, value.updateTime)
        if index._isFullVld():
            self.val[index.val] = value.clone()
        else:
            self.val = {}

    def __setitem__(self, index, value):
        assert isinstance(self, Value)
        assert index._dtype == INT, index._dtype
        return self._setitem__val(index, value)

    def _eq__val(self, other):
        assert self._dtype.elmType == other._dtype.elmType
        assert self._dtype.size == other._dtype.size

        eq = True
        first = self.val[0]
        vld = first.vldMask
        updateTime = first.updateTime
        if self.vldMask and other.vldMask:
            for a, b in zip(self.val, other.val):
                eq = eq and a == b
                vld = vld & a.vldMask & b.vldMask
                updateTime = max(updateTime, a.updateTime, b.updateTime)
        else:
            eq = False
            vld = 0
        return BOOL.getValueCls()(eq, BOOL, vld, updateTime)

    def _eq(self, other):
        assert isinstance(other, ArrayVal)
        return self._eq__val(other)
