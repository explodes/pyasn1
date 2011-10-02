# BER encoder
from pyasn1.type import base, tag, univ, char, useful
from pyasn1.codec.ber import eoo
from pyasn1 import error

class Error(Exception): pass

class AbstractItemEncoder:
    supportIndefLenMode = 1
    def encodeTag(self, t, isConstructed):
        tagClass, tagFormat, tagId = t.asTuple()  # this is a hotspot
        v = tagClass | tagFormat
        if isConstructed:
            v = v|tag.tagFormatConstructed
        if tagId < 31:
            return chr(v|tagId)
        else:
            s = chr(tagId&0x7f)
            tagId = tagId >> 7
            while tagId:
                s = chr(0x80|(tagId&0x7f)) + s
                tagId = tagId >> 7
            return chr(v|0x1F) + s

    def encodeLength(self, length, defMode):
        if not defMode and self.supportIndefLenMode:
            return '\x80'
        if length < 0x80:
            return chr(length)
        else:
            substrate = ''
            while length:
                substrate = chr(length&0xff) + substrate
                length = length >> 8
            substrateLen = len(substrate)
            if substrateLen > 126:
                raise Error('Length octets overflow (%d)' % substrateLen)
            return chr(0x80 | substrateLen) + substrate

    def encodeValue(self, encodeFun, value, defMode, maxChunkSize):
        raise Error('Not implemented')

    def _encodeEndOfOctets(self, encodeFun, defMode):
        if defMode or not self.supportIndefLenMode:
            return ''
        else:
            return encodeFun(eoo.endOfOctets, defMode)
        
    def encode(self, encodeFun, value, defMode, maxChunkSize):
        substrate, isConstructed = self.encodeValue(
            encodeFun, value, defMode, maxChunkSize
            )
        tagSet = value.getTagSet()
        if tagSet:
            if not isConstructed:  # primitive form implies definite mode
                defMode = 1
            return self.encodeTag(
                tagSet[-1], isConstructed
                ) + self.encodeLength(
                len(substrate), defMode
                ) + substrate + self._encodeEndOfOctets(encodeFun, defMode)
        else:
            return substrate  # untagged value

class EndOfOctetsEncoder(AbstractItemEncoder):
    def encodeValue(self, encodeFun, value, defMode, maxChunkSize):
        return '', 0

class ExplicitlyTaggedItemEncoder(AbstractItemEncoder):
    def encodeValue(self, encodeFun, value, defMode, maxChunkSize):
        if isinstance(value, base.AbstractConstructedAsn1Item):
            value = value.clone(tagSet=value.getTagSet()[:-1],
                                cloneValueFlag=1)
        else:
            value = value.clone(tagSet=value.getTagSet()[:-1])
        return encodeFun(value, defMode, maxChunkSize), 1

explicitlyTaggedItemEncoder = ExplicitlyTaggedItemEncoder()

class IntegerEncoder(AbstractItemEncoder):
    supportIndefLenMode = 0
    def encodeValue(self, encodeFun, value, defMode, maxChunkSize):
        octets = []
        value = int(value) # to save on ops on asn1 type
        while 1:
            octets.insert(0, value & 0xff)
            if value == 0 or value == -1:
                break
            value = value >> 8
        if value == 0 and octets[0] & 0x80:
            octets.insert(0, 0)
        while len(octets) > 1 and \
                  (octets[0] == 0 and octets[1] & 0x80 == 0 or \
                   octets[0] == 0xff and octets[1] & 0x80 != 0):
            del octets[0]
        return ''.join([chr(x) for x in octets]), 0

class BitStringEncoder(AbstractItemEncoder):
    def encodeValue(self, encodeFun, value, defMode, maxChunkSize):
        if not maxChunkSize or len(value) <= maxChunkSize*8:
            r = {}; l = len(value); p = 0; j = 7
            while p < l:
                i, j = divmod(p, 8)
                r[i] = r.get(i,0) | value[p]<<(7-j)
                p = p + 1
            keys = list(r); keys.sort()
            return chr(7-j) + ''.join([chr(r[k]) for k in keys]), 0
        else:
            pos = 0; substrate = ''
            while 1:
                # count in octets
                v = value.clone(value[pos*8:pos*8+maxChunkSize*8])
                if not v:
                    break
                substrate = substrate + encodeFun(v, defMode, maxChunkSize)
                pos = pos + maxChunkSize
            return substrate, 1

class OctetStringEncoder(AbstractItemEncoder):
    def encodeValue(self, encodeFun, value, defMode, maxChunkSize):
        if not maxChunkSize or len(value) <= maxChunkSize:
            return str(value), 0
        else:
            pos = 0; substrate = ''
            while 1:
                v = value.clone(value[pos:pos+maxChunkSize])
                if not v:
                    break
                substrate = substrate + encodeFun(v, defMode, maxChunkSize)
                pos = pos + maxChunkSize
            return substrate, 1

class NullEncoder(AbstractItemEncoder):
    supportIndefLenMode = 0
    def encodeValue(self, encodeFun, value, defMode, maxChunkSize):
        return '', 0

class ObjectIdentifierEncoder(AbstractItemEncoder):
    supportIndefLenMode = 0
    precomputedValues = {
        (1, 3, 6, 1, 2): ('+', '\x06', '\x01', '\x02'),        
        (1, 3, 6, 1, 4): ('+', '\x06', '\x01', '\x04')
        }
    def encodeValue(self, encodeFun, value, defMode, maxChunkSize):    
        oid = value.asTuple()
        if oid[:5] in self.precomputedValues:
            octets = self.precomputedValues[oid[:5]]
            index = 5
        else:
            if len(oid) < 2:
                raise error.PyAsn1Error('Short OID %s' % value)

            # Build the first twos
            index = 0
            subid = oid[index] * 40
            subid = subid + oid[index+1]
            if subid < 0 or subid > 0xff:
                raise error.PyAsn1Error(
                    'Initial sub-ID overflow %s in OID %s' % (oid[index:], value)
                    )
            octets = (chr(subid),)
            index = index + 2

        # Cycle through subids
        for subid in oid[index:]:
            if subid > -1 and subid < 128:
                # Optimize for the common case
                octets = octets + (chr(subid & 0x7f),)
            elif subid < 0 or subid > 0xFFFFFFFF:
                raise error.PyAsn1Error(
                    'SubId overflow %s in %s' % (subid, value)
                    )
            else:
                # Pack large Sub-Object IDs
                res = (chr(subid & 0x7f),)
                subid = subid >> 7
                while subid > 0:
                    res = (chr(0x80 | (subid & 0x7f)),) + res
                    subid = subid >> 7 
                # Convert packed Sub-Object ID to string and add packed
                # it to resulted Object ID
                octets = octets + (''.join(res),)
                
        return ''.join(octets), 0

class RealEncoder(AbstractItemEncoder):
    def encodeValue(self, encodeFun, value, defMode, maxChunkSize):
        if value.isPlusInfinity():
            return '\x40', 0
        if value.isMinusInfinity():
            return '\x41', 0
        m, b, e = value
        if not m:
            return '', 0
        if b == 10:
            return '\x03%dE%s%d' % (m, e == 0 and '+' or '', e), 0
        elif b == 2:
            fo = 0x80                 # binary enoding
            if m < 0:
                fo = fo | 0x40  # sign bit
                m = -m
            while int(m) != m: # drop floating point
                m *= 2
                e -= 1
            while m & 0x1 == 0: # mantissa normalization
                m >>= 1
                e += 1
            eo = ''
            while e:
                eo = chr(e&0xff) + eo
                e >>= 8
            n = len(eo)
            if n > 0xff:
                raise error.PyAsn1Error('Real exponent overflow')
            if n == 1:
                pass
            elif n == 2:
                fo |= 1
            elif n == 3:
                fo |= 2
            else:
                fo |= 3
                eo = chr(n//0xff+1) + eo
            po = ''
            while m:
                po = chr(m&0xff) + po
                m >>= 8
            substrate = chr(fo) + eo + po
            return substrate, 0
        else:
            raise error.PyAsn1Error('Prohibited Real base %s' % b)

class SequenceEncoder(AbstractItemEncoder):
    def encodeValue(self, encodeFun, value, defMode, maxChunkSize):
        value.setDefaultComponents()
        value.verifySizeSpec()
        substrate = ''; idx = len(value)
        while idx > 0:
            idx = idx - 1
            if value[idx] is None:  # Optional component
                continue
            component = value.getDefaultComponentByPosition(idx)
            if component is not None and component == value[idx]:
                continue
            substrate = encodeFun(
                value[idx], defMode, maxChunkSize
                ) + substrate
        return substrate, 1

class SequenceOfEncoder(AbstractItemEncoder):
    def encodeValue(self, encodeFun, value, defMode, maxChunkSize):
        value.verifySizeSpec()
        substrate = ''; idx = len(value)
        while idx > 0:
            idx = idx - 1
            substrate = encodeFun(
                value[idx], defMode, maxChunkSize
                ) + substrate
        return substrate, 1

class ChoiceEncoder(AbstractItemEncoder):
    def encodeValue(self, encodeFun, value, defMode, maxChunkSize):
        return encodeFun(value.getComponent(), defMode, maxChunkSize), 1

class AnyEncoder(OctetStringEncoder):
    def encodeValue(self, encodeFun, value, defMode, maxChunkSize):
        return str(value), defMode == 0

tagMap = {
    eoo.endOfOctets.tagSet: EndOfOctetsEncoder(),
    univ.Boolean.tagSet: IntegerEncoder(),
    univ.Integer.tagSet: IntegerEncoder(),
    univ.BitString.tagSet: BitStringEncoder(),
    univ.OctetString.tagSet: OctetStringEncoder(),
    univ.Null.tagSet: NullEncoder(),
    univ.ObjectIdentifier.tagSet: ObjectIdentifierEncoder(),
    univ.Enumerated.tagSet: IntegerEncoder(),
    univ.Real.tagSet: RealEncoder(),
    # Sequence & Set have same tags as SequenceOf & SetOf
    univ.SequenceOf.tagSet: SequenceOfEncoder(),
    univ.SetOf.tagSet: SequenceOfEncoder(),
    univ.Choice.tagSet: ChoiceEncoder(),
    # character string types
    char.UTF8String.tagSet: OctetStringEncoder(),
    char.NumericString.tagSet: OctetStringEncoder(),
    char.PrintableString.tagSet: OctetStringEncoder(),
    char.TeletexString.tagSet: OctetStringEncoder(),
    char.VideotexString.tagSet: OctetStringEncoder(),
    char.IA5String.tagSet: OctetStringEncoder(),
    char.GraphicString.tagSet: OctetStringEncoder(),
    char.VisibleString.tagSet: OctetStringEncoder(),
    char.GeneralString.tagSet: OctetStringEncoder(),
    char.UniversalString.tagSet: OctetStringEncoder(),
    char.BMPString.tagSet: OctetStringEncoder(),
    # useful types
    useful.GeneralizedTime.tagSet: OctetStringEncoder(),
    useful.UTCTime.tagSet: OctetStringEncoder()        
    }

# Type-to-codec map for ambiguous ASN.1 types
typeMap = {
    univ.Set.typeId: SequenceEncoder(),
    univ.SetOf.typeId: SequenceOfEncoder(),
    univ.Sequence.typeId: SequenceEncoder(),
    univ.SequenceOf.typeId: SequenceOfEncoder(),
    univ.Choice.typeId: ChoiceEncoder(),
    univ.Any.typeId: AnyEncoder()
    }

class Encoder:
    def __init__(self, tagMap, typeMap={}):
        self.__tagMap = tagMap
        self.__typeMap = typeMap

    def __call__(self, value, defMode=1, maxChunkSize=0):
        tagSet = value.getTagSet()
        if len(tagSet) > 1:
            concreteEncoder = explicitlyTaggedItemEncoder
        else:
            if value.typeId is not None and value.typeId in self.__typeMap:
                concreteEncoder = self.__typeMap[value.typeId]
            elif tagSet in self.__tagMap:
                concreteEncoder = self.__tagMap[tagSet]
            else:
                baseTagSet = value.baseTagSet
                if baseTagSet in self.__tagMap:
                    concreteEncoder = self.__tagMap[baseTagSet]
                else:
                    raise Error('No encoder for %s' % value)
        return concreteEncoder.encode(
            self, value, defMode, maxChunkSize
            )

encode = Encoder(tagMap, typeMap)
