# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# Name:         noteworthy/binaryTranslate.py
# Purpose:      parses .nwc binary files, compressed and uncompressed
#
# Authors:      Michael Scott Cuthbert
#
# Copyright:    Copyright © 2006-2013 Michael Scott Cuthbert and the music21 Project
# License:      BSD, see license.txt
# ------------------------------------------------------------------------------
'''
Attempts at reading pure .nwc files in music21

First will solve uncompressed .nwc then compressed .nwc

Thanks to Juria90 and the nwc2xml project for solving so many of the documentation problems.
No part of this code is taken from that project, but this project would have been impossible
without his work.

Translates .nwc into .nwctxt and then uses Jordi Guillen's .nwctxt translator to go from
there to music21.

BETA -- does not work for many file elements and is untested.

Demo, showing the extent of problems.  The measure numbers are not set.  Lyrics are missing
and the triplet in the AltoClef part is omitted.  This is very beta.  Much better would be to
convert the file into .xml or .nwctxt first.

::

    >>> #_DOCS_SHOW c = converter.parse('/Users/cuthbert/desktop/cuthbert_test1.nwc')
    >>> p = common.getSourceFilePath() / 'noteworthy' / 'cuthbert_test1.nwc' #_DOCS_HIDE
    >>> c = converter.parse(str(p)) #_DOCS_HIDE
    >>> c.show('text')
    {0.0} <music21.stream.Part ...>
        {0.0} <music21.stream.Measure 0 offset=0.0>
            {0.0} <music21.clef.TrebleClef>
            {0.0} <music21.meter.TimeSignature 4/4>
            {0.0} <music21.note.Note G>
            {1.0} <music21.note.Note C>
            {2.0} <music21.note.Note C>
            {3.0} <music21.note.Note B>
        {4.0} <music21.stream.Measure 0 offset=4.0>
            {0.0} <music21.note.Note C>
    {0.0} <music21.stream.Part ...>
        {0.0} <music21.stream.Measure 0 offset=0.0>
            {0.0} <music21.clef.TrebleClef>
            {0.0} <music21.meter.TimeSignature 4/4>
            {0.0} <music21.note.Note G>
            {1.0} <music21.note.Note A>
            {2.0} <music21.note.Note A>
            {3.5} <music21.note.Note G>
        {4.0} <music21.stream.Measure 0 offset=4.0>
            {0.0} <music21.note.Note G>
    {0.0} <music21.stream.Part ...>
        {0.0} <music21.stream.Measure 0 offset=0.0>
            {0.0} <music21.clef.AltoClef>
            {0.0} <music21.meter.TimeSignature 4/4>
            {0.0} <music21.note.Note D>
            {2.0} <music21.note.Note C#>
            {3.0} <music21.note.Note D>
            {4.0} <music21.note.Note E>
        {5.0} <music21.stream.Measure 0 offset=5.0>
            {0.0} <music21.note.Note E>
    {0.0} <music21.stream.Part ...>
        {0.0} <music21.stream.Measure 0 offset=0.0>
            {0.0} <music21.clef.BassClef>
            {0.0} <music21.meter.TimeSignature 4/4>
            {0.0} <music21.note.Note G>
            {1.0} <music21.note.Note F>
            {2.0} <music21.note.Note E>
            {3.0} <music21.note.Note G>
        {4.0} <music21.stream.Measure 0 offset=4.0>
            {0.0} <music21.note.Note C>

'''
import struct
from music21 import environment
from music21 import exceptions21

from music21.noteworthy import constants

environLocal = environment.Environment('noteworthy.translate')


class NoteworthyBinaryTranslateException(exceptions21.Music21Exception):
    pass


class NWCConverter:
    '''
    A converter object for binary .nwc files.  Do not normally use directly; use converter.parse.

    >>> fp = '/Users/cuthbert/test.nwc'
    >>> nwcc = noteworthy.binaryTranslate.NWCConverter(fp=fp)
    >>> nwcc
    <music21.noteworthy.binaryTranslate.NWCConverter object at 0x...>
    >>> nwcc.fp
    '/Users/cuthbert/test.nwc'
    >>> nwcc.fileContents is None
    True
    >>> nwcc.parsePosition
    0
    >>> nwcc.version  # version of nwc file to be parsed
    200
    >>> nwcc.numberOfStaves
    0
    >>> nwcc.staves
    []
    '''

    def __init__(self, *args, **keywords):
        if 'fp' in keywords:
            self.fp = keywords['fp']
        else:
            self.fp = None
        self.fileContents = None
        self.parsePosition = 0
        self.version = 200
        self.numberOfStaves = 0
        self.titlePageInfo = 0
        self.pageNumberStart = 0
        self.staves = []
        self.comment = None
        self.fonts = []
        self.lyricist = None
        self.groupVisibility = None
        self.allowLayering = None
        self.margins = None
        self.notationTypeface = None
        self.extendLastSystem = None
        self.copyright1 = None
        self.copyright2 = None
        self.increaseNoteSpacing = None
        self.author = None
        self.title = None
        self.measureStart = None
        self.measureNumbers = None
        self.mirrorMargins = None
        self.staffLabels = None
        self.sins = None
        self.user = None
        self.staffHeight = 0

    # noinspection SpellCheckingInspection
    def parseFile(self, fp=None):
        r'''
        Parse a file (calls .toStream)

        >>> #_DOCS_SHOW fp = '/Users/cuthbert/desktop/cuthbert_test1.nwc'
        >>> fp = str(common.getSourceFilePath()/'noteworthy'/'cuthbert_test1.nwc') #_DOCS_HIDE
        >>> nwcc = noteworthy.binaryTranslate.NWCConverter(fp=fp)
        >>> nwcc.fileContents
        >>> streamObj = nwcc.parseFile()
        >>> len(nwcc.fileContents)  # binary
        1139
        >>> nwcc.fileContents[0:80]
        b'[NoteWorthy ArtWare]\x00\x00\x00[NoteWorthy
                 Composer]\x00\x01\x02\x02\x00\x00\x00N/A\x000_JldRQMSKq6M5a3FQqK_g\x00\x00\x00'
        >>> streamObj
        <music21.stream.Score ...>
        '''
        if fp is None:
            fp = self.fp
        with open(str(fp), 'rb') as f:  # remove in Py3.6...
            self.fileContents = f.read()
        self.parseContent()
        return self.toStream()

    def parseString(self, bytesIn=None):
        '''
        same as parseFile but takes a string (in Py3, bytes) of binary data instead.
        '''
        self.fileContents = bytesIn
        self.parseContent()
        return self.toStream()

    def readLEShort(self, updateParsePosition=True):
        '''
        Helper module: read a little-endian short value to an integer

        >>> nwcc = noteworthy.binaryTranslate.NWCConverter()
        >>> nwcc.fileContents = b'\x02\x01\x03\x01'
        >>> nwcc.parsePosition
        0
        >>> nwcc.readLEShort()
        258
        >>> nwcc.parsePosition
        2
        >>> nwcc.readLEShort()
        259
        >>> nwcc.parsePosition
        4

        Or to not update the parsePosition, send False:
        >>> nwcc.parsePosition = 0
        >>> nwcc.readLEShort(False)
        258
        >>> nwcc.readLEShort(False)
        258
        >>> nwcc.parsePosition
        0
        '''
        fc = self.fileContents
        pp = self.parsePosition
        value = struct.unpack('<h', fc[pp:pp + 2])[0]

        if updateParsePosition is True:
            self.parsePosition = pp + 2
        return value

    def byteToInt(self, updateParsePosition=True):
        '''
        changes a byte into an unsigned int
        (i.e., if the byte is > 127 then it's subtracted from 256)
        '''
        fc = self.fileContents
        pp = self.parsePosition
        value = ord(fc[pp:pp + 1])
        # print(value)
        if updateParsePosition is True:
            self.parsePosition = pp + 1
        return value

    def byteToSignedInt(self, updateParsePosition=True):
        '''
        changes a byte into a signed int
        (i.e., if the byte is > 127 then it's subtracted from 256)
        '''
        val = self.byteToInt(updateParsePosition)
        if val > 127:
            val = val - 256
        return val

    def readBytes(self, bytesToRead=1, updateParsePosition=True):
        '''
        reads the next bytesToRead bytes and then (optionally) updates self.parsePosition
        '''
        fc = self.fileContents
        pp = self.parsePosition
        value = fc[pp:pp + bytesToRead]
        if updateParsePosition is True:
            self.parsePosition = pp + bytesToRead
        return value

    def readToNUL(self, updateParsePosition=True):
        r'''
        reads self.fileContents up to, but not including, the next position of \x00.

        updates the parsePosition unless updateParsePosition is False
        '''
        fc = self.fileContents
        try:
            nulPosition = fc.index(0, self.parsePosition)
        except ValueError:
            nulPosition = -1
            # raise NoteworthyBinaryTranslateException(fc[self.parsePosition:],
            #             self.parsePosition)
        # print(self.parsePosition, nulPosition)
        ret = None
        if nulPosition == -1:
            ret = fc[self.parsePosition:]
        else:
            ret = fc[self.parsePosition:nulPosition]
        if updateParsePosition is True:
            self.parsePosition = nulPosition + 1
        return ret

    def isValidNWCFile(self, updateParsePosition=True):
        storedPP = self.parsePosition
        self.parsePosition = 0
        header1 = self.readToNUL()
        if header1 != b'[NoteWorthy ArtWare]':
            return False
        junk = self.readToNUL()
        junk = self.readToNUL()
        header2 = self.readToNUL()
        if header2 != '[NoteWorthy Composer]':
            return False
        if updateParsePosition is False and storedPP != 0:
            self.parsePosition = storedPP
        return True

    # thanks to Juria90 for figuring these out! and so much more!
    versionFromHex = {0x0114: 120,
                      0x011E: 130,
                      0x0132: 150,
                      0x0137: 155,
                      0x0146: 170,
                      0x014B: 175,
                      0x0200: 200,
                      0x0201: 201,
                      }

    def fileVersion(self, updateParsePosition=True):
        storedPP = self.parsePosition
        self.parsePosition = 45
        fileVersionRaw = self.readLEShort(updateParsePosition)
        if updateParsePosition is False:
            self.parsePosition = storedPP
        if fileVersionRaw in self.versionFromHex:
            self.version = self.versionFromHex[fileVersionRaw]
        else:
            print('No Version Found! Most likely a newer version.  Using 2.01')
            self.version = 201  # most likely a newer version

        return self.version

    def skipBytes(self, numBytes=1):
        self.parsePosition += numBytes

    def advanceToNotNUL(self, nul=b'\x00'):
        pp = self.parsePosition
        fc = self.fileContents
        # the slice Notation [pp:pp + 1] is needed to avoid Py3 conversion to bytes
        while fc[pp:pp + 1] == nul:
            pp += 1
        self.parsePosition = pp

    def parseContent(self):
        '''
        the main parse routine called by parseFile() or parseString()
        '''
        if self.fileContents[0:6] == b'[NWZ]\x00':
            import zlib
            fcNew = zlib.decompress(self.fileContents[6:])
            self.fileContents = fcNew

        self.parsePosition = 0
        self.parseHeader()
        self.staves = []
        # print(self.numberOfStaves)

        for i in range(self.numberOfStaves):
            # process only visible staves
            if not self.groupVisibility or ord(self.groupVisibility) & 2**i:
                thisStaff = NWCStaff(parent=self)
                thisStaff.parseStaff()
                # FIXME exclude percussion as it can not be exported as musicxml for now
                if thisStaff.instrumentName != 'Gunshot':
                    self.staves.append(thisStaff)

    def parseHeader(self):
        '''
        Sets a ton of information from the header, and advances the parse position.
        '''
        self.isValidNWCFile()
        self.fileVersion()

        # print(self.version)
        # print(self.parsePosition)
        self.skipBytes(4)  # skipping registered vs. unregistered
        # print(self.parsePosition)
        self.user = self.readToNUL()
        # print(self.user)
        unused_unknown = self.readToNUL()
        # print(unused_unknown)
        self.skipBytes(10)
        self.title = self.readToNUL()
        # print(self.title)
        self.author = self.readToNUL()
        # print(self.author)
        if self.version >= 200:
            self.lyricist = self.readToNUL()
            # print(self.lyricist)
        else:
            self.lyricist = None
        self.copyright1 = self.readToNUL()
        self.copyright2 = self.readToNUL()
        self.comment = self.readToNUL()
        # print(self.comment)
        self.extendLastSystem = self.readToNUL()
        self.increaseNoteSpacing = self.readToNUL()
        unused = self.readToNUL()
        self.measureNumbers = self.readToNUL()

        unused = self.readToNUL()
        self.measureStart = self.readLEShort()
        if self.version >= 130:
            self.margins = self.readToNUL()
            # split by space
        else:
            self.margins = '0.0 0.0 0.0 0.0'
        self.sins = self.readToNUL()
        unused = self.readToNUL()
        if self.version >= 130:
            self.groupVisibility = self.readToNUL()
            self.allowLayering = self.readToNUL()
        else:
            self.groupVisibility = True
            self.allowLayering = True
        if self.version >= 200:
            self.notationTypeface = self.readToNUL()
        else:
            self.notationTypeface = 'Maestro'
        self.staffHeight = self.readLEShort()

        if self.version > 170:
            fontCount = 12
        elif self.version > 130:
            fontCount = 10  # some 170 have 12 font info.  See Juria90's code for workaround.
        else:
            fontCount = 0
        self.advanceToNotNUL()  # should not be needed, but some parse errors
        self.skipBytes(2)
        self.fonts = []
        for i in range(fontCount):
            fontDict = {
                'name': self.readToNUL(),
                'style': self.byteToInt(),
                'size': self.byteToInt(),
            }
            unused = self.byteToInt()
            fontDict['charset'] = self.byteToInt()
            if fontDict['name'] == b'':
                fontDict['name'] = b'Times New Roman'
            if fontDict['style'] == 0:
                fontDict['style'] = 0  # regular; 1 = bold; 2 = italic; 3 = bold italic???
            if fontDict['size'] == 0:
                fontDict['size'] = 12
            self.fonts.append(fontDict)
            # ansi charset is default; but we don't use
        # print(self.fonts)
        self.titlePageInfo = self.byteToInt()

        # index of [None, First Systems, Top Systems, All Systems]
        self.staffLabels = self.byteToInt()
        self.pageNumberStart = self.readLEShort()
        if self.version >= 200:
            self.skipBytes(1)
        self.numberOfStaves = self.byteToInt()
        # print('StaffCount', self.numberOfStaves)
        self.skipBytes(1)

    def dumpToNWCText(self):
        infos = '|SongInfo|Title:' + self.title.decode('latin_1')
        infos += '|Author:' + self.author.decode('latin_1')
        dumpObjects = [infos]
        for s in self.staves:
            self.previousAlteration = {}
            staffDumpObjects = s.dump()
            for sdo in staffDumpObjects:
                dumpObjects.append(sdo)

        #print(dumpObjects)
        return dumpObjects

    def toStream(self):
        from music21.noteworthy import translate
        nwt = translate.NoteworthyTranslator()
        s = nwt.parseList(self.dumpToNWCText())
        return s


class NWCStaff:
    def __init__(self, parent=None):
        self.parent = parent
        self.lyrics = []
        self.objects = []
        self.instrumentName = None
        self.group = None
        self.layerWithNextStaff = None
        self.transposition = None
        self.partVolume = None
        self.stereoPan = None
        self.color = 0
        self.alignSyllable = None
        self.numberOfLyrics = 0
        self.numberOfObjects = 0
        self.lines = 0
        self.name = None
        self.staffOffset = 0
        self.label = None
        self.lyricAlignment = 0

    def parseStaff(self):
        # environLocal.warn([self.parent.parsePosition, self.objects])
        self.parseHeader()
        # environLocal.warn(['header done', self.parent.parsePosition, self.objects])
        self.parseLyrics()
        # environLocal.warn(['lyrics done', self.parent.parsePosition, self.objects])
        self.parseObjects()
        # environLocal.warn([self.parent.parsePosition, self.objects])

    def dump(self):
        dumpObjects = []
        if self.label == None:
            self.label = self.instrumentName if self.instrumentName != None else "NoName"
        dumpObjects.append('|AddStaff|Name:' + self.label)
        instru = '|Name:' + self.instrumentName
        patch = '|Patch:' + str(constants.MidiInstruments.index(self.instrumentName))
        transpo = '|Trans:' + str(self.transposition)
        dumpObjects.append('|StaffInstrument' + instru + patch + transpo)
        for o in self.objects:
            dm = o.dumpMethod
            d = dm(o)
            if d != '':
                dumpObjects.append(d)

        return dumpObjects

    def parseHeader(self):
        p = self.parent
        # p = NWCConverter()
        self.name = p.readToNUL()
        # print('staff name:', self.name)
        if p.version >= 200:
            self.label = p.readToNUL()
            # print('label:', self.label)
            self.instrumentName = p.readToNUL()
        else:
            self.label = None
            self.instrumentName = None
        self.group = p.readToNUL()
        # print('unknown : ', p.fileContents[p.parsePosition:p.parsePosition+27])
        # print "group: ", self.group

        if p.version >= 200:
           # self.endingBar = p.byteToInt()
           # self.muted = p.byteToInt()
           # junk = p.byteToInt()
           # self.channel = p.byteToInt()
           # junk = p.byteToInt()
           # self.playbackDevice = p.byteToInt()
           # junk = p.byteToInt()
           # self.patchBank = p.byteToInt()
           # junk = p.byteToInt()
           # self.patchName = p.byteToInt()
           # junk = p.byteToInt()
           # self.defaultVelocity = p.byteToInt()
           # self.style = p.readLEShort()
           # self.verticalSizeUpper = p.readLEShort()
           # self.verticalSizeLower = p.readLEShort()

            p.skipBytes(27)
            self.lines = p.byteToInt()
            # print "lines:", self.lines
            # print "position:", p.parsePosition
            self.layerWithNextStaff = p.readLEShort()
            self.transposition = p.readLEShort()
            self.partVolume = p.readLEShort()
            self.stereoPan = p.readLEShort()
            self.color = p.byteToInt()
            self.alignSyllable = p.readLEShort()
            self.numberOfLyrics = p.readLEShort()

        elif p.version == 175:
            p.skipBytes(11)
            instruPatch = p.byteToInt()
            if instruPatch < len(constants.MidiInstruments):
                self.instrumentName = constants.MidiInstruments[instruPatch - 1]
            p.skipBytes(10)
            self.transposition = p.byteToSignedInt()
            p.skipBytes(6)
            self.alignSyllable = p.readLEShort()
            self.numberOfLyrics = p.readLEShort()

        if self.numberOfLyrics > 0:
            self.lyricAlignment = p.readLEShort()
            self.staffOffset = p.readLEShort()
        else:
            self.lyricAlignment = 0
            self.staffOffset = 0
        # print('Number of lyrics:', self.numberOfLyrics)

    def parseLyrics(self):

        p = self.parent
        lyrics = []

        for i in range(self.numberOfLyrics):
            syllables = []
            try:
                lyricBlockSize = p.readLEShort()
            except struct.error:
                lyricBlockSize = 0
                environLocal.warn('Could not read lyrics. Trying with zero length.')
            # print('lyric block size: ', lyricBlockSize)

            if lyricBlockSize > 0:
                unused_lyricSize = p.readLEShort()
                parsePositionStart = p.parsePosition

                # print('lyric Size: ', lyricSize)
                junk = p.readLEShort()
                continueIt = True
                maxRead = 1000
                while continueIt is True and maxRead > 0:
                    syllable = p.readToNUL()
                    # environLocal.warn([p.parsePosition, syllable, 'syllable'])
                    maxRead -= 1
                    # print('syllable: ', syllable)
                    if syllable == b'':
                        continueIt = False
                    else:
                        syllables.append(syllable)
                p.parsePosition = parsePositionStart + lyricBlockSize
                lyrics.append(syllables)
            # print(syllables)
        # print(lyrics)
        if self.numberOfLyrics > 0:
            junk = p.readLEShort()
        junk_2 = p.readLEShort()
        # print(p.parsePosition)
        self.lyrics = lyrics
        return lyrics

    def parseObjects(self):
        p = self.parent
        objects = []
        self.numberOfObjects = p.readLEShort()
        if p.version > 150:
            self.numberOfObjects -= 2

        for i in range(self.numberOfObjects):
            thisObject = NWCObject(staffParent=self, parserParent=p)
            thisObject.parseObject()
            objects.append(thisObject)
        self.objects = objects
        # print(objects)
        return objects


class NWCObject:
    def __init__(self, staffParent=None, parserParent=None):
        self.staffParent = staffParent
        self.parserParent = parserParent
        self.type = None
        self.placement = 0
        self.pos = 0
        self.style = 0
        self.localRepeatCount = 0
        self.data = 0
        self.data1 = None
        self.data2 = None
        self.data3 = None
        self.delay = 0
        self.clefType = 0
        self.offset = 0
        self.visible = 0
        self.duration = 0
        self.durationStr = None
        self.font = 0
        self.sharps = 0
        self.octaveShift = 0
        self.octaveShiftName = None
        self.clefName = None
        self.attribute1 = None
        self.attribute2 = 0
        self.stemLength = 0
        self.dots = 0
        self.bits = 0
        self.denominator = 0
        self.tieInfo = ''
        self.volume = 0
        self.base = 0
        self.velocity = 0
        self.count = 0
        self.name = None
        self.value = 0
        self.flats = 0
        self.keyString = ''
        self.numerator = 0
        self.alterationStr = ''
        self.dotAttribute = None
        self.text = None

        def genericDumpMethod(inner_self):
            return ''

        self.dumpMethod = genericDumpMethod

    def parseObject(self):
        '''
        determine what type of object I am, and set things accordingly
        '''
        p = self.parserParent
        objectType = p.readLEShort() # a number -- an index in the objMethods list
        # print("new object " + str(objectType))
        if objectType >= len(self.objMethods) or objectType < 0:
            raise NoteworthyBinaryTranslateException(
                'Cannot translate objectType: %d; max is %d' % (objectType, len(self.objMethods)))
        if p.version >= 170:
            self.visible = p.byteToInt()
        else:
            self.visible = 0

        objectMethod = self.objMethods[objectType]

        objectMethod(self)

    # Start parsing specific objects
    # =================================

    def clef(self):
        '''
        clef info,
        4 bytes
        '''
        p = self.parserParent
        # print('Clef at : ', p.parsePosition)
        self.type = 'Clef'
        self.clefType = p.readLEShort()
        self.octaveShift = p.readLEShort()

        if self.clefType < len(constants.ClefNames):
            self.clefName = constants.ClefNames[self.clefType]
        if self.octaveShift < len(constants.OctaveShiftNames):
            self.octaveShiftName = constants.OctaveShiftNames[self.octaveShift]

        # print('now at: ', p.parsePosition)
        def dump(inner_self):
            build = '|Clef|'
            if inner_self.staffParent.instrumentName == 'Gunshot':
                inner_self.clefName = 'Percussion'
            if inner_self.clefName:
                build += 'Type:' + inner_self.clefName + '|'
            if inner_self.octaveShiftName:
                build += 'OctaveShift:' + inner_self.octaveShiftName + '|'
            return build

        self.dumpMethod = dump

    def keySig(self):
        '''
        Key signature
        10 bytes
        '''
        p = self.parserParent
        self.type = 'KeySig'
        self.flats = p.byteToInt()
        p.skipBytes(1)  # ?
        self.sharps = p.byteToInt()
        p.skipBytes(7)

        # too complex...
        # for letter in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
        #     bitshift = ord(letter) - ord('A')
        #     letterMask = 1 << bitshift

        if self.flats > 0 and self.flats in constants.FlatMask:
            self.keyString = constants.FlatMask[self.flats]
        elif self.sharps > 0 and self.sharps in constants.SharpMask:
            self.keyString = constants.SharpMask[self.sharps]
        else:
            self.keyString = ''  # no unusual key signatures

        def dump(inner_self):
            build = '|Key|Signature:' + inner_self.keyString
            return build

        self.dumpMethod = dump

    def barline(self):
        '''
        Bar line
        2 bytes
        '''
        p = self.parserParent
        self.type = 'Barline'
        self.style = p.byteToInt()
        self.localRepeatCount = p.byteToInt()

        def dump(self):
            self.parserParent.previousAlteration = {}
            build = '|Bar|'
            if self.style > 0 and self.style < len(constants.styles):
                # dont care about Single, it is the default
                styleString = constants.styles[self.style]
                build += '|Style:' + styleString
            return build

        self.dumpMethod = dump

    def ending(self):
        '''
        Endings
        2 bytes
        '''
        p = self.parserParent
        self.type = 'Ending'
        self.style = p.byteToInt()
        p.skipBytes(1)

        def dump(self):
            build = '|Ending|Endings:' + str(self.style)
            return build

        self.dumpMethod = dump

    def instrument(self):
        '''
        Instrument
        8 bytes
        '''
        p = self.parserParent
        self.type = 'Instrument'
        p.skipBytes(8)
        #TODO size ??
        self.name = p.readToNUL()
        p.skipBytes(1)
        p.skipBytes(8)  # velocity

    def timeSig(self):
        '''
        Time signature
        6 bytes
        '''
        p = self.parserParent
        self.type = 'TimeSignature'
        self.numerator = p.readLEShort()
        self.bits = p.readLEShort()
        self.denominator = 1 << self.bits
        self.style = p.readLEShort()

        def dump(inner_self):
            build = '|TimeSig|Signature:%d/%d' % (inner_self.numerator, inner_self.denominator)
            return build

        self.dumpMethod = dump

    def tempo(self):
        '''
        Tempo indications
        5 bytes + null terminated string
        '''
        p = self.parserParent
        self.type = 'Tempo'
        self.pos = p.byteToInt()
        self.placement = p.byteToInt()
        self.value = p.readLEShort()
        self.base = p.byteToInt()
        if p.version < 170:
            junk = p.readLEShort()
        self.text = p.readToNUL()

        def dump(inner_self):
            build = '|Tempo|Tempo:%d' % inner_self.value
            return build

        self.dumpMethod = dump


    def dynamic(self):
        '''
        dynamics
        7 bytes
        '''
        p = self.parserParent
        self.type = 'Dynamic'
        if p.version < 170:
            print('Dynamics on version below 1.70 is not supported yet')
        else:
            self.pos = p.byteToInt()
            self.placement = p.byteToInt()
            self.style = p.byteToInt()
            self.velocity = p.readLEShort()
            self.volume = p.readLEShort()

    def setDurationForObject(self):
        '''
        get duration string for note or rest
        '''

        durationValues = ['Whole', 'Half', '4th', '8th', '16th', '32nd', '64th']
        durStr = durationValues[self.duration]

        grace = 0
        if self.type == 'Note':
            self.dotAttribute = self.attribute1[0]
            grace = self.attribute1[1] & 0x20
        else:
            self.dotAttribute = self.data2[3]

        ordDot = self.dotAttribute

        if (ordDot & 0x01) > 0:
            self.dots = 2
        elif (ordDot & 0x04) > 0:
            self.dots = 1
        else:
            self.dots = 0

        if self.dots == 1:
            durStr += ',Dotted'
        elif self.dots == 2:
            durStr += ',DblDotted'

        if grace > 0:
            durStr += ',Grace'

        return durStr

    def note(self):
        '''
        Note
        8 bytes
        '''
        p = self.parserParent
        self.type = 'Note'
        # print('Note at parse position: ', p.parsePosition)
        if p.version < 170:
            print('Cannot yet handle versions before 170')
        else:
            self.duration = p.byteToInt()
            self.data2 = p.readBytes(3)  # ??
            self.attribute1 = p.readBytes(2)
            # print(hex(ord(self.attribute1[0])))
            self.pos = p.byteToSignedInt()
            self.pos = -1 * self.pos
            self.attribute2 = p.byteToInt()
            if p.version <= 170:
                self.data3 = p.readBytes(2)
            else:
                self.data3 = None
            if p.version >= 200:
                if (self.attribute2 & 0x40) != 0:
                    # print('have stemLength info!')
                    self.stemLength = p.byteToInt()
                else:
                    # print('attribute 2:', hex(self.attribute2))
                    self.stemLength = 7
            else:
                self.stemLength = 7
            # if p.version >= 200 and (self.attribute2 & 0x40) != 0:
            #    self.stemLength = p.byteToInt()
            # else:
            #    self.stemLength = 7
        # uh oh!!!
        # p.skipBytes(2)
        # print('Now at: ', p.parsePosition)
        # print('Duration: ', self.duration)
        # print('Data2: ',)
        # for i in self.data2:
        #     print(hex(ord(i)),)
        # print('...')

        self.durationStr = self.setDurationForObject()

        alterationTexts = ['#', 'b', 'n', '##', 'bb', '']
        alterationIndex = self.attribute2 & 0x07
        if alterationIndex < len(alterationTexts):
            self.alterationStr = alterationTexts[alterationIndex]
        else:
            self.alterationStr = ''

        self.tieInfo = ''
        ordAtt1 = self.attribute1[0]
        if (ordAtt1 & 0x10) > 0:
            self.tieInfo = '^'

        def dump(inner_self):
            build = '|Note|Dur:' + inner_self.durationStr + '|'

            # in NWC, alteration is not specified for other octave
            alteration = inner_self.alterationStr
            if alteration == '':
                alteration = inner_self.parserParent.previousAlteration.get(inner_self.pos % 7)
            if alteration == None:
                alteration = ''

            build += ('Pos:'
                      + alteration
                      + str(inner_self.pos)
                      + inner_self.tieInfo + '|')
            inner_self.parserParent.previousAlteration[inner_self.pos % 7] = inner_self.alterationStr
            return build

        self.dumpMethod = dump

    def rest(self):
        '''
        Rest
        8 bytes
        '''
        p = self.parserParent
        self.type = 'Rest'
        if p.version <= 150:
            print('igg...')
        else:
            self.duration = p.byteToInt()
            self.data2 = p.readBytes(5)
            self.offset = p.readLEShort()

        self.durationStr = self.setDurationForObject()

        def dump(inner_self):
            build = '|Rest|Dur:' + inner_self.durationStr + '|'
            return build

        self.dumpMethod = dump

    def noteChordMember(self):
        '''
        Chord member
        8 bytes + n Note objects
        '''

        p = self.parserParent
        self.type = 'NoteChordMember'
        numberOfNotes = 0
        if p.version <= 170:
            self.data1 = p.readBytes(12)
        elif p.version == 175:
            self.data1 = p.readBytes(10)
            numberOfNotes = self.data1[8]
        else:
            self.data1 = p.readBytes(8)
        if p.version >= 200:
            if (self.data1[7] & 0x40) != 0:
                print('have stemLength info!')
                self.stemLength = p.byteToInt()
            else:
                # print('attribute 2:', hex(self.attribute2))
                self.stemLength = 7
        else:
            self.stemLength = 7

        self.data2 = []
        for i in range(numberOfNotes):
            chordNote = NWCObject(staffParent=self, parserParent=p)
            chordNote.parseObject()
            self.data2.append(chordNote)
 
        def dump(self):
            build = '|Chord'
            notes = {}
            for d in self.data2:
                if notes.get(d.durationStr) == None:
                    notes[d.durationStr] = []

                notes[d.durationStr].append(d.alterationStr + str(d.pos) + d.tieInfo)

            for n in notes:
                build += '|Dur:' + n + '|Pos:' + ','.join(notes[n])

            return build

        self.dumpMethod = dump



    def pedal(self):
        '''
        Pedal
        3 bytes
        '''
        p = self.parserParent
        self.type = 'Pedal'
        if p.version < 170:
            print('Pedal on version below 170 is not yet supported')
        else:
            self.pos = p.byteToInt()
            self.placement = p.byteToInt()
            self.style = p.byteToInt()

    def flowDir(self):
        '''
        Flow
        4 bytes
        '''
        p = self.parserParent
        self.type = 'FlowDir'
        if p.version >= 170:
            self.pos = p.byteToInt()
            self.placement = p.byteToInt()
        else:
            self.pos = -8  # so needs to be signed int?
            self.placement = 0x01

        self.style = p.readLEShort()

    def mpc(self):
        '''
        Midi Instructions
        34 bytes
        '''
        p = self.parserParent
        self.type = 'MPC'
        self.pos = p.byteToInt()
        self.placement = p.byteToInt()
        if p.version == 175:
            self.data1 = p.readBytes(32)
        elif p.version > 155:
            self.data1 = p.readBytes(31)
        else:
            self.data1 = p.readBytes(32)

    def tempoVariation(self):
        '''
        Tempo variation
        4 bytes
        '''
        p = self.parserParent
        self.type = 'TempoVariation'
        if p.version >= 170:
            self.pos = p.byteToInt()
            self.placement = p.byteToInt()
            self.style = p.byteToInt()
            self.delay = p.byteToInt()
        else:
            self.style = p.byteToInt()
            self.style = self.style & 0x0F
            self.pos = p.byteToInt()
            self.placement = p.byteToInt()
            self.delay = p.byteToInt()

    def dynamicVariation(self):
        '''
        Dynamic variation
        3 bytes
        '''
        p = self.parserParent
        self.type = 'DynamicVariation'
        self.pos = p.byteToInt()
        if p.version >= 170:
            self.placement = p.byteToInt()
        else:
            self.placement = 0
        self.style = p.byteToInt()

    def performance(self):
        '''
        Performance
        3 bytes
        '''
        p = self.parserParent
        self.type = 'Performance'
        self.pos = p.byteToInt()
        if p.version >= 170:
            self.placement = p.byteToInt()
        else:
            self.placement = 0
        self.style = p.byteToInt()

    def textObj(self):
        '''
        Text
        3 bytes + null terminated string
        '''
        p = self.parserParent
        self.type = 'Text'
        self.pos = p.byteToInt()
        self.data = p.byteToInt()
        self.font = p.byteToInt()
        self.text = p.readToNUL()

        # first text obj may be staff label
        if self.staffParent.label == None:
            self.staffParent.label = self.text.decode('latin_1')
            self.text = None

        def dump(inner_self):
            build = "|Text|Text:" + inner_self.text.decode('latin_1') 
            return build

        if self.text != None:
            self.dumpMethod = dump


    def restChordMember(self):
        '''
        Rest chord
        10 bytes
        '''
        p = self.parserParent
        self.type = 'RestChordMember'
        self.count = p.readLEShort()
        p.skipBytes(8)

    objMethods = [clef            ,#0
                  keySig          ,#1
                  barline         ,#2
                  ending          ,#3
                  instrument      ,#4
                  timeSig         ,#5
                  tempo           ,#6
                  dynamic         ,#7
                  note            ,#8
                  rest            ,#9
                  noteChordMember ,#10
                  pedal           ,#11
                  flowDir         ,#12
                  mpc             ,#13
                  tempoVariation  ,#14
                  dynamicVariation,#15
                  performance     ,#16
                  textObj         ,#17
                  restChordMember  #18
                  ]

if __name__ == '__main__':
    import music21
    music21.mainTest()
    # fp = '/Users/cuthbert/Desktop/395.nwc'
    # fp = 'http://www.cpdl.org/brianrussell/358.nwc'
    # from music21 import converter
    # s = converter.parse(fp)
    # s.show()

    # nwc = NWCConverter()
    # s = nwc.parseFile(fp)
    # s.show()
    # print(nwc.dumpToNWCText())
    # print(nwc.isValidNWCFile())
    # print(nwc.fileVersion())
