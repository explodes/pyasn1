from pyasn1.type import tag, namedtype, univ
from pyasn1.codec.ber import encoder
from pyasn1.compat.octets import ints2octs
from pyasn1.error import PyAsn1Error
from sys import version_info
if version_info[0:2] < (2, 7) or \
   version_info[0:2] in ( (3, 0), (3, 1) ):
    try:
        import unittest2 as unittest
    except ImportError:
        import unittest
else:
    import unittest

class LargeTagEncoderTestCase(unittest.TestCase):
    def setUp(self):
        self.o = univ.Integer().subtype(
            value=1, explicitTag=tag.Tag(tag.tagClassApplication, tag.tagFormatSimple, 0xdeadbeaf)
            )
    def testEncoder(self):
        assert encoder.encode(self.o) == ints2octs((127, 141, 245, 182, 253, 47, 3, 2, 1, 1))
        
class IntegerEncoderTestCase(unittest.TestCase):
    def testPosInt(self):
        assert encoder.encode(univ.Integer(12)) == ints2octs((2, 1, 12))
        
    def testNegInt(self):
        assert encoder.encode(univ.Integer(-12)) == ints2octs((2, 1, 244))
        
    def testZero(self):
        assert encoder.encode(univ.Integer(0)) == ints2octs((2, 1, 0))

    def testCompactZero(self):
        encoder.IntegerEncoder.supportCompactZero = True
        substrate = encoder.encode(univ.Integer(0))
        encoder.IntegerEncoder.supportCompactZero = False
        assert substrate == ints2octs((2, 0))
        
    def testMinusOne(self):
        assert encoder.encode(univ.Integer(-1)) == ints2octs((2, 1, 255))
        
    def testPosLong(self):
        assert encoder.encode(
            univ.Integer(0xffffffffffffffff)
            ) == ints2octs((2, 9, 0, 255, 255, 255, 255, 255, 255, 255, 255))
        
    def testNegLong(self):
        assert encoder.encode(
            univ.Integer(-0xffffffffffffffff)
            ) == ints2octs((2, 9, 255, 0, 0, 0, 0, 0, 0, 0, 1))

class BooleanEncoderTestCase(unittest.TestCase):
    def testTrue(self):
        assert encoder.encode(univ.Boolean(1)) == ints2octs((1, 1, 1))
        
    def testFalse(self):
        assert encoder.encode(univ.Boolean(0)) == ints2octs((1, 1, 0))

class BitStringEncoderTestCase(unittest.TestCase):
    def setUp(self):
        self.b = univ.BitString((1,0,1,0,1,0,0,1,1,0,0,0,1,0,1))
        
    def testDefMode(self):
        assert encoder.encode(self.b) == ints2octs((3, 3, 1, 169, 138))
        
    def testIndefMode(self):
        assert encoder.encode(
            self.b, defMode=0
            ) == ints2octs((3, 3, 1, 169, 138))
        
    def testDefModeChunked(self):
        assert encoder.encode(
            self.b, maxChunkSize=1
            ) == ints2octs((35, 8, 3, 2, 0, 169, 3, 2, 1, 138))
        
    def testIndefModeChunked(self):
        assert encoder.encode(
            self.b, defMode=0, maxChunkSize=1
            ) == ints2octs((35, 128, 3, 2, 0, 169, 3, 2, 1, 138, 0, 0))
        
    def testEmptyValue(self):
        assert encoder.encode(univ.BitString(())) == ints2octs((3, 1, 0))
        
class OctetStringEncoderTestCase(unittest.TestCase):
    def setUp(self):
        self.o = univ.OctetString('Quick brown fox')
        
    def testDefMode(self):
        assert encoder.encode(self.o) == ints2octs((4, 15, 81, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 32, 102, 111, 120))
        
    def testIndefMode(self):
        assert encoder.encode(
            self.o, defMode=0
            ) == ints2octs((4, 15, 81, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 32, 102, 111, 120))

    def testDefModeChunked(self):
        assert encoder.encode(
            self.o, maxChunkSize=4
            ) == ints2octs((36, 23, 4, 4, 81, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 4, 111, 119, 110, 32, 4, 3, 102, 111, 120))

    def testIndefModeChunked(self):
        assert encoder.encode(
            self.o, defMode=0, maxChunkSize=4
            ) == ints2octs((36, 128, 4, 4, 81, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 4, 111, 119, 110, 32, 4, 3, 102, 111, 120, 0, 0))
        
class ExpTaggedOctetStringEncoderTestCase(unittest.TestCase):
    def setUp(self):
        self.o = univ.OctetString().subtype(
            value='Quick brown fox',
            explicitTag=tag.Tag(tag.tagClassApplication,tag.tagFormatSimple,5)
            )
    def testDefMode(self):
        assert encoder.encode(self.o) == ints2octs((101, 17, 4, 15, 81, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 32, 102, 111, 120))

    def testIndefMode(self):
        assert encoder.encode(
            self.o, defMode=0
            ) == ints2octs((101, 128, 4, 15, 81, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 32, 102, 111, 120, 0, 0))
        
    def testDefModeChunked(self):
        assert encoder.encode(
            self.o, defMode=1, maxChunkSize=4
            ) == ints2octs((101, 25, 36, 23, 4, 4, 81, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 4, 111, 119, 110, 32, 4, 3, 102, 111, 120))
        
    def testIndefModeChunked(self):
        assert encoder.encode(
            self.o, defMode=0, maxChunkSize=4
            ) == ints2octs((101, 128, 36, 128, 4, 4, 81, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 4, 111, 119, 110, 32, 4, 3, 102, 111, 120, 0, 0, 0, 0))

class NullEncoderTestCase(unittest.TestCase):
    def testNull(self):
        assert encoder.encode(univ.Null('')) == ints2octs((5, 0))

class ObjectIdentifierEncoderTestCase(unittest.TestCase):
    def testOne(self):
        assert encoder.encode(
            univ.ObjectIdentifier((1,3,6,0,0xffffe))
        ) == ints2octs((6, 6, 43, 6, 0, 191, 255, 126))

    def testEdge1(self):
        assert encoder.encode(
            univ.ObjectIdentifier((0,39))
        ) == ints2octs((6,1,39))

    def testEdge2(self):
        assert encoder.encode(
            univ.ObjectIdentifier((1,39))
        ) == ints2octs((6,1,79))

    def testEdge3(self):
        #10010000|10000000|10000000|10000000|01001111
        assert encoder.encode(
            univ.ObjectIdentifier((2,0xffffffff))
        ) == ints2octs((6,5,0x90,0x80,0x80,0x80,0x4F))

    def testEdge4(self):
        #01111111
        assert encoder.encode(
            univ.ObjectIdentifier((2,47))
        ) == ints2octs((6,1,0x7F))

    def testEdge5(self):
        #10000001|00000000
        assert encoder.encode(
            univ.ObjectIdentifier((2,48))
        ) == ints2octs((6,2,0x81,0x00))

    def testEdge6(self):
        #10000001|00110100|00000003
        assert encoder.encode(
            univ.ObjectIdentifier((2,100,3))
        ) == ints2octs((6,3,0x81,0x34,0x03))

    def testEdge7(self):
        #10000101|00000000
        assert encoder.encode(
            univ.ObjectIdentifier((2,560))
        ) == ints2octs((6,2,133,00))

    def testEdge8(self):
        #10001000|10000100|10000111|0000010
        assert encoder.encode(
            univ.ObjectIdentifier((2,16843570))
        ) == ints2octs((6,4,0x88,0x84,0x87,0x02))

class RealEncoderTestCase(unittest.TestCase):
    def testChar(self):
        assert encoder.encode(
            univ.Real((123, 10, 11))
            ) == ints2octs((9, 7, 3, 49, 50, 51, 69, 49, 49))

    def testBin1(self):
        assert encoder.encode( # default binEncBase = 2
            univ.Real((0.5, 2, 0)) # check encbase = 2 and exponenta = -1
            ) == ints2octs((9, 3, 128, 255, 1))

    def testBin2(self):
        r = univ.Real((3.25, 2, 0)) 
        r.binEncBase = 8 # change binEncBase only for this instance of Real
        assert encoder.encode(
            r # check encbase = 8
            ) == ints2octs((9, 3, 148, 255, 13))

    def testBin3(self):
        # change binEncBase in the RealEncoder instance => for all further Reals
        encoder.tagMap[univ.Real.tagSet].binEncBase = 16
        assert encoder.encode(
            univ.Real((0.00390625, 2, 0)) # check encbase = 16
            ) == ints2octs((9, 3, 160, 254, 1))

    def testBin4(self):
        # choose binEncBase automatically for all further Reals (testBin[4-7])
        encoder.tagMap[univ.Real.tagSet].binEncBase = None 
        assert encoder.encode(
            univ.Real((1, 2, 0)) # check exponenta = 0
            ) == ints2octs((9, 3, 128, 0, 1))

    def testBin5(self):
        assert encoder.encode(
            univ.Real((3, 2, -1020)) # case of 2 octs for exponenta and
                                     # negative exponenta and abs(exponenta) is
                                     # all 1's and fills the whole octet(s) 
            ) == ints2octs((9, 4, 161, 255, 1, 3))

    def testBin6(self):
        assert encoder.encode(
            univ.Real((1, 2, 262140)) # case of 3 octs for exponenta and
                                      # check that first 9 bits for exponenta
                                      # are not all 1's
            ) == ints2octs((9, 5, 162, 0, 255, 255, 1))

    def testBin7(self):
        assert encoder.encode(
            univ.Real((-1, 2, 76354972)) # case of >3 octs for exponenta and
                                         # mantissa < 0
            ) == ints2octs((9, 7, 227, 4, 1, 35, 69, 103, 1))


    def testPlusInf(self):
        assert encoder.encode(univ.Real('inf')) == ints2octs((9, 1, 64))

    def testMinusInf(self):
        assert encoder.encode(univ.Real('-inf')) == ints2octs((9, 1, 65))
        
    def testZero(self):
        assert encoder.encode(univ.Real(0)) == ints2octs((9, 0))
        
class SequenceEncoderTestCase(unittest.TestCase):
    def setUp(self):
        self.s = univ.Sequence(componentType=namedtype.NamedTypes(
            namedtype.NamedType('place-holder', univ.Null('')),
            namedtype.OptionalNamedType('first-name', univ.OctetString('')),
            namedtype.DefaultedNamedType('age', univ.Integer(33)),
            ))

    def __init(self):
        self.s.clear()
        self.s.setComponentByPosition(0)
        
    def __initWithOptional(self):
        self.s.clear()
        self.s.setComponentByPosition(0)
        self.s.setComponentByPosition(1, 'quick brown')
        
    def __initWithDefaulted(self):
        self.s.clear()
        self.s.setComponentByPosition(0)
        self.s.setComponentByPosition(2, 1)
        
    def __initWithOptionalAndDefaulted(self):
        self.s.clear()
        self.s.setComponentByPosition(0, univ.Null(''))
        self.s.setComponentByPosition(1, univ.OctetString('quick brown'))
        self.s.setComponentByPosition(2, univ.Integer(1))
        
    def testDefMode(self):
        self.__init()
        assert encoder.encode(self.s) == ints2octs((48, 2, 5, 0))
        
    def testIndefMode(self):
        self.__init()
        assert encoder.encode(
            self.s, defMode=0
            ) == ints2octs((48, 128, 5, 0, 0, 0))

    def testDefModeChunked(self):
        self.__init()
        assert encoder.encode(
            self.s, defMode=1, maxChunkSize=4
            ) == ints2octs((48, 2, 5, 0))

    def testIndefModeChunked(self):
        self.__init()
        assert encoder.encode(
            self.s, defMode=0, maxChunkSize=4
            ) == ints2octs((48, 128, 5, 0, 0, 0))

    def testWithOptionalDefMode(self):
        self.__initWithOptional()
        assert encoder.encode(self.s) == ints2octs((48, 15, 5, 0, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110))
        
    def testWithOptionalIndefMode(self):
        self.__initWithOptional()
        assert encoder.encode(
            self.s, defMode=0
            ) == ints2octs((48, 128, 5, 0, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 0, 0))

    def testWithOptionalDefModeChunked(self):
        self.__initWithOptional()
        assert encoder.encode(
            self.s, defMode=1, maxChunkSize=4
            ) == ints2octs((48, 21, 5, 0, 36, 17, 4, 4, 113, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 3, 111, 119, 110))

    def testWithOptionalIndefModeChunked(self):
        self.__initWithOptional()
        assert encoder.encode(
            self.s, defMode=0, maxChunkSize=4
            ) == ints2octs((48, 128, 5, 0, 36, 128, 4, 4, 113, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 3, 111, 119, 110, 0, 0, 0, 0))

    def testWithDefaultedDefMode(self):
        self.__initWithDefaulted()
        assert encoder.encode(self.s) == ints2octs((48, 5, 5, 0, 2, 1, 1))
        
    def testWithDefaultedIndefMode(self):
        self.__initWithDefaulted()
        assert encoder.encode(
            self.s, defMode=0
            ) == ints2octs((48, 128, 5, 0, 2, 1, 1, 0, 0))

    def testWithDefaultedDefModeChunked(self):
        self.__initWithDefaulted()
        assert encoder.encode(
            self.s, defMode=1, maxChunkSize=4
            ) == ints2octs((48, 5, 5, 0, 2, 1, 1))

    def testWithDefaultedIndefModeChunked(self):
        self.__initWithDefaulted()
        assert encoder.encode(
            self.s, defMode=0, maxChunkSize=4
            ) == ints2octs((48, 128, 5, 0, 2, 1, 1, 0, 0))

    def testWithOptionalAndDefaultedDefMode(self):
        self.__initWithOptionalAndDefaulted()
        assert encoder.encode(self.s) == ints2octs((48, 18, 5, 0, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 2, 1, 1))
        
    def testWithOptionalAndDefaultedIndefMode(self):
        self.__initWithOptionalAndDefaulted()
        assert encoder.encode(
            self.s, defMode=0
            ) == ints2octs((48, 128, 5, 0, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 2, 1, 1, 0, 0))

    def testWithOptionalAndDefaultedDefModeChunked(self):
        self.__initWithOptionalAndDefaulted()
        assert encoder.encode(
            self.s, defMode=1, maxChunkSize=4
            ) == ints2octs((48, 24, 5, 0, 36, 17, 4, 4, 113, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 3, 111, 119, 110, 2, 1, 1))

    def testWithOptionalAndDefaultedIndefModeChunked(self):
        self.__initWithOptionalAndDefaulted()
        assert encoder.encode(
            self.s, defMode=0, maxChunkSize=4
            ) == ints2octs((48, 128, 5, 0, 36, 128, 4, 4, 113, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 3, 111, 119, 110, 0, 0, 2, 1, 1, 0, 0))

class ChoiceEncoderTestCase(unittest.TestCase):
    def setUp(self):
        self.s = univ.Choice(componentType=namedtype.NamedTypes(
            namedtype.NamedType('place-holder', univ.Null('')),
            namedtype.NamedType('number', univ.Integer(0)),
            namedtype.NamedType('string', univ.OctetString())
            ))

    def testEmpty(self):
        try:
            encoder.encode(self.s)
        except PyAsn1Error:
            pass
        else:
            assert 0, 'encoded unset choice'
        
    def testFilled(self):
        self.s.setComponentByPosition(0, univ.Null(''))
        assert encoder.encode(self.s) == ints2octs((5, 0))

    def testTagged(self):
        s = self.s.subtype(
            explicitTag=tag.Tag(tag.tagClassContext,tag.tagFormatConstructed,4)
        )
        s.setComponentByPosition(0, univ.Null(''))
        assert encoder.encode(s) == ints2octs((164, 2, 5, 0))

    def testUndefLength(self):
        self.s.setComponentByPosition(2, univ.OctetString('abcdefgh'))
        assert encoder.encode(self.s, defMode=False, maxChunkSize=3) == ints2octs((36, 128, 4, 3, 97, 98, 99, 4, 3, 100, 101, 102, 4, 2, 103, 104, 0, 0))

    def testTaggedUndefLength(self):
        s = self.s.subtype(
            explicitTag=tag.Tag(tag.tagClassContext,tag.tagFormatConstructed,4)
        )
        s.setComponentByPosition(2, univ.OctetString('abcdefgh'))
        assert encoder.encode(s, defMode=False, maxChunkSize=3) == ints2octs((164, 128, 36, 128, 4, 3, 97, 98, 99, 4, 3, 100, 101, 102, 4, 2, 103, 104, 0, 0, 0, 0))

class AnyEncoderTestCase(unittest.TestCase):
    def setUp(self):
        self.s = univ.Any(encoder.encode(univ.OctetString('fox')))
        
    def testUntagged(self):
        assert encoder.encode(self.s) == ints2octs((4, 3, 102, 111, 120))
            
    def testTaggedEx(self):
        s = self.s.subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 4)
            )
        assert encoder.encode(s) == ints2octs((164, 5, 4, 3, 102, 111, 120))

    def testTaggedIm(self):
        s = self.s.subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 4)
            )
        assert encoder.encode(s) == ints2octs((132, 5, 4, 3, 102, 111, 120))
                    
if __name__ == '__main__': unittest.main()
