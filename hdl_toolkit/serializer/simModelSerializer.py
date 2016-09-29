from jinja2.environment import Environment
from jinja2.loaders import PackageLoader
from keyword import kwlist

from hdl_toolkit.hdlObjects.types.enum import Enum
from hdl_toolkit.hdlObjects.types.enumVal import EnumVal
from hdl_toolkit.hdlObjects.value import Value
from hdl_toolkit.serializer.exceptions import SerializerException
from hdl_toolkit.serializer.nameScope import LangueKeyword, NameScope
from hdl_toolkit.serializer.simModelSerializer_Value import SimModelSerializer_value
from hdl_toolkit.serializer.simModelSerializer_ops import SimModelSerializer_ops
from hdl_toolkit.serializer.simModelSerializer_types import SimModelSerializer_types
from hdl_toolkit.serializer.utils import maxStmId
from hdl_toolkit.synthesizer.param import Param, evalParam
from hdl_toolkit.synthesizer.rtlLevel.mainBases import RtlSignalBase
from python_toolkit.arrayQuery import where
from hdl_toolkit.hdlObjects.statements import IfContainer
from hdl_toolkit.hdlObjects.operator import Operator
from hdl_toolkit.hdlObjects.operatorDefs import AllOps


env = Environment(loader=PackageLoader('hdl_toolkit', 'serializer/templates_simModel'))
unitTmpl = env.get_template('modelCls.py')
processTmpl = env.get_template('process.py')
iftmpl = env.get_template("if.py")

_indent = "    "
_indentCache = {}        
def getIndent(indentNum):
    try:
        return  _indentCache[indentNum]
    except KeyError:
        i = "".join([_indent for _ in range(indentNum)])   
        _indentCache[indentNum] = i
        return i

class SimModelSerializer(SimModelSerializer_value, SimModelSerializer_ops, SimModelSerializer_types):
    __keywords_dict = {kw: LangueKeyword() for kw in kwlist}
    __keywords_dict.update({'sim': LangueKeyword(),
                            'self': LangueKeyword()})
    fileExtension = '.py'
    formater = lambda s: s
    
    @classmethod
    def getBaseNameScope(cls):
        s = NameScope(True)
        s.setLevel(1)
        s[0].update(cls.__keywords_dict)
        return s
    
    @classmethod
    def serializationDecision(cls, obj, serializedClasses, serializedConfiguredUnits):
        # we need all instances for simulation
        return True
    
    @classmethod
    def asHdl(cls, obj):
        if isinstance(obj, RtlSignalBase):
            return cls.SignalItem(obj)
        elif isinstance(obj, Value):
            return cls.Value(obj)
        else:
            try:
                serFn = getattr(cls, obj.__class__.__name__)
            except AttributeError:
                raise NotImplementedError("Not implemented for %s" % (repr(obj)))
            return serFn(obj)
    
    @classmethod
    def stmAsHdl(cls, obj, indent=0, default=None):
        try:
            serFn = getattr(cls, obj.__class__.__name__)
        except AttributeError:
            raise NotImplementedError("Not implemented for %s" % (repr(obj)))
        return serFn(obj, indent, default)
    
    @classmethod
    def FunctionContainer(cls, fn):
        raise NotImplementedError()
        # return fn.name
    @classmethod
    def Entity(cls, ent, scope):
        ent.name = scope.checkedName(ent.name, ent, isGlobal=True)
        return ""
        
    @classmethod
    def Architecture(cls, arch, scope):
        variables = []
        procs = []
        extraTypes = set()
        extraTypes_serialized = []
        arch.variables.sort(key=lambda x: x.name)
        arch.processes.sort(key=lambda x: (x.name, maxStmId(x)))
        arch.componentInstances.sort(key=lambda x: x._name)
        
        for v in arch.variables:
            t = v._dtype
            # if type requires extra definition
            if isinstance(t, Enum) and t not in extraTypes:
                extraTypes.add(v._dtype)
                extraTypes_serialized.append(cls.HdlType(t, scope, declaration=True))

            v.name = scope.checkedName(v.name, v)
            variables.append(v)
            
        
        def serializeVar(v):
            dv = evalParam(v.defaultVal)
            if isinstance(dv, EnumVal):
                dv = "%s.%s" % (dv._dtype.name, dv.val)
            else:
                dv = cls.Value(dv)
            
            return v.name, cls.HdlType(v._dtype), dv
        
        for p in arch.processes:
            procs.append(cls.HWProcess(p, scope, 0))
        
        # architecture names can be same for different entities
        # arch.name = scope.checkedName(arch.name, arch, isGlobal=True)    
             
        return unitTmpl.render({
        "name"               : arch.getEntityName(),
        "ports"              : list(map(lambda p: (p.name, cls.HdlType(p._dtype)), arch.entity.ports)),
        "signals"            : list(map(serializeVar, variables)),
        "extraTypes"         : extraTypes_serialized,
        "processes"          : procs,
        "processObjects"     : arch.processes,
        "processesNames"     : map(lambda p: p.name, arch.processes),
        "componentInstances" : arch.componentInstances,
        })
   
    @classmethod
    def Assignment(cls, a, indent=0, default=None):
        dst = a.dst
        if a.indexes is not None:
            return "%syield (self.%s, %s, (%s,), %s)" % (
                        getIndent(indent), dst.name, cls.Value(a.src),
                        ", ".join(map(cls.asHdl, a.indexes)),
                        a.isEventDependent)
        else:
            if not (dst._dtype == a.src._dtype):
                raise SerializerException("%s <= %s  is not valid assignment\n because types are different (%s; %s) " % 
                     (cls.asHdl(dst), cls.Value(a.src), repr(dst._dtype), repr(a.src._dtype)))
            return "%syield (self.%s, %s, %s)" % (
                        getIndent(indent), dst.name, cls.Value(a.src),
                        a.isEventDependent)
            

        
    @classmethod
    def comment(cls, comentStr):
        return "#" + comentStr.replace("\n", "\n#")     

    @classmethod
    def condAsHdl(cls, cond):
        cond = list(cond)
        return "%s" % (",".join(map(lambda x: cls.asHdl(x), cond)))
    
    @classmethod
    def IfContainer(cls, ifc, indent, default=None):
        cond = cls.condAsHdl(ifc.cond)
        ifTrue = ifc.ifTrue
        ifFalse = ifc.ifFalse

        if ifc.elIfs:
            # if has elifs revind this to tree
            ifFalse = []
            topIf = IfContainer(ifc.cond, ifc.ifTrue, ifFalse)
            for c, stms in ifc.elIfs:
                _ifFalse = []
                lastIf = IfContainer(c, stms, _ifFalse)
                ifFalse.append(lastIf)
                ifFalse = _ifFalse
            
            lastIf.ifFalse = ifc.ifFalse
            
            return cls.IfContainer(topIf, indent, default)
        else:
            if default is not None:
                default=cls.stmAsHdl(default, indent + 1)
            return iftmpl.render(
                indent=getIndent(indent),
                indentNum=indent,
                cond=cond,
                default=default,
                ifTrue=tuple(map(lambda obj: cls.stmAsHdl(obj, indent + 1),
                                 ifTrue)),
                ifFalse=tuple(map(lambda obj: cls.stmAsHdl(obj, indent + 1),
                                   ifFalse)))  
    
    @classmethod
    def SwitchContainer(cls, sw, indent, default=None):
        switchOn = sw.switchOn
        mkCond = lambda c: {Operator(AllOps.EQ,
                                    [switchOn, c])}
        ifFalse = []
        elIfs = []
        
        for key, statements in sw.cases:
            if key is not None:  # None is default
                elIfs.append((mkCond(key), statements))  
            else:
                ifFalse = statements
        
        topCond = mkCond(sw.cases[0][0])
        topIf = IfContainer(topCond,
                    sw.cases[0][1],
                    ifFalse,
                    elIfs)
        
        return cls.IfContainer(topIf, indent, default=default)
    
    @classmethod
    def WaitStm(cls, w):
        if w.isTimeWait:
            return "wait for %d ns" % w.waitForWhat
        elif w.waitForWhat is None:
            return "wait"
        else:
            raise NotImplementedError()
    
    @classmethod
    def HWProcess(cls, proc, scope, indentLvl):
        body = proc.statements
        proc.name = scope.checkedName(proc.name, proc)
        sensitivityList = sorted(where(proc.sensitivityList,
                                       lambda x : not isinstance(x, Param)), key=lambda x: x.name)
        if len(body) == 1:
            _body = cls.stmAsHdl(body[0], 2)
        elif len(body) == 2:
            # first statement is taken as default
            _body = cls.stmAsHdl(body[1], 2, body[0])
        
        return processTmpl.render({
              "name": proc.name,
              "sensitivityList": [s.name for s in sensitivityList],
              "stmLines": [_body] })
           


