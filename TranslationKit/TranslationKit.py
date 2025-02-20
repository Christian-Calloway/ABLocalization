import os, re
from deep_translator import GoogleTranslator

class TransFileHandler:

    def __init__(self, sourcePath='./', destinationPath='./', resultPath='./', fileName="", tranlationName='Tchinese') -> None:
        self.sourcePath = sourcePath
        self.destinationPath = destinationPath
        self.resultPath = resultPath
        self.fileName = fileName
        if fileName:
            with open(self.destinationPath+self.fileName, 'r', encoding="utf-8") as fn, open(self.sourcePath+self.fileName, 'r', encoding="utf-8") as fo:
                self.rawDestinationFile = fn.readlines()
                self.rawSourceFile = fo.readlines()
        self.findHashPattern = 'translate '+tranlationName
        self.stringsBlockPattern = self.findHashPattern+' strings:\n'

    def findDiff(self, followOrginOrder=True) -> None:
        diffPath = 'diff/'
        diffPrefix = 'diff_'
        fnl = [line for line in self.rawDestinationFile if not line.isspace() and '#' not in line]
        fol = [line for line in self.rawSourceFile if not line.isspace() and '#' not in line]
        fnlHash = [re.sub(r"\s*"+re.escape(self.findHashPattern+' '), '' ,line)[:-2] for line in fnl if self.findHashPattern in line]
        folHash = [re.sub(r"\s*"+re.escape(self.findHashPattern+' '), '' ,line)[:-2] for line in fol if self.findHashPattern in line]
        fnlHashSet = set(fnlHash)
        folHashSet = set(folHash)
        diffResult = fnlHashSet-folHashSet
        followOriginOrderDiffResult = [fH for fH in fnlHash if fH in diffResult]

        if not os.path.isdir(self.resultPath+diffPath):
            os.makedirs(self.resultPath+diffPath, mode=0o777)

        with open(self.resultPath+diffPath+diffPrefix+self.fileName, 'w', encoding="utf-8") as r:
            if followOrginOrder:
                for line in followOriginOrderDiffResult:
                    r.write(line+'\n')
            else:
                for line in sorted(list(diffResult)):
                    r.write(line+'\n')

    def initNewTransFile(self, stringsBlockOverride=False, dupHashOverride=True, editFullwidthPunctuation=True, useMT=False) -> None:
        fnRefinedDict = self.normalizeFile(self.rawDestinationFile, dupHashOverride, editFullwidthPunctuation=False)
        foRefinedDict = self.normalizeFile(self.rawSourceFile, dupHashOverride, editFullwidthPunctuation)

        if fnRefinedDict['cotainStringsBlock'] and not stringsBlockOverride:
            workScope = len(fnRefinedDict['orderedHash'])-1
        else:
            workScope = len(fnRefinedDict['orderedHash'])

        notMatcedhContentIndex = []
        notMatcedhContent = []
        for i in range(workScope):
            try:
                pos = foRefinedDict['orderedHash'].index(fnRefinedDict['orderedHash'][i])
                fnRefinedDict['content'][i][fnRefinedDict['orderedHash'][i]] = foRefinedDict['content'][pos][foRefinedDict['orderedHash'][pos]]
            except:
                if useMT:
                    notMatcedhContentIndex.append(i)
                    notMatcedhContent.append(self.getLineContent(fnRefinedDict['content'][i][fnRefinedDict['orderedHash'][i]][3]))
                else:
                    tmpInfo = self.getLineContent(fnRefinedDict['content'][i][fnRefinedDict['orderedHash'][i]][3])
                    fnRefinedDict['content'][i][fnRefinedDict['orderedHash'][i]][3] = fnRefinedDict['content'][i][fnRefinedDict['orderedHash'][i]][3][:tmpInfo['startPos']]+'@@@'+tmpInfo['line']+'"'
        if notMatcedhContent:
            translated = []
            batchLines = [line['line'] for line in notMatcedhContent]
            #make data pages
            #Google Translate limits 6,000,000 characters per minute, 5 requests/second/user and 200,000 requests/day (Billable limit). https://stackoverflow.com/questions/4405861/google-translate-api-requests-limit
            for i in range(0, len(batchLines), 100):
                try:
                    translated.extend(GoogleTranslator(source='en', target='zh-TW').translate_batch(batchLines[i:i+100]))
                except:
                    translated.extend(GoogleTranslator(source='en', target='zh-TW').translate_batch(batchLines[i:]))
            for i in range(len(notMatcedhContentIndex)):
                if translated[i]:
                    fnRefinedDict['content'][notMatcedhContentIndex[i]][fnRefinedDict['orderedHash'][notMatcedhContentIndex[i]]][3] = fnRefinedDict['content'][notMatcedhContentIndex[i]][fnRefinedDict['orderedHash'][notMatcedhContentIndex[i]]][3][:notMatcedhContent[i]['startPos']]+'@@@'+translated[i]+'"'
                else:
                    fnRefinedDict['content'][notMatcedhContentIndex[i]][fnRefinedDict['orderedHash'][notMatcedhContentIndex[i]]][3] = fnRefinedDict['content'][notMatcedhContentIndex[i]][fnRefinedDict['orderedHash'][notMatcedhContentIndex[i]]][3][:notMatcedhContent[i]['startPos']]+'@@@"'

        outputContent = []
        outputContent.extend(fnRefinedDict['headerWords'])
        for i in range(len(fnRefinedDict['orderedHash'])):
            outputContent.extend(fnRefinedDict['content'][i][fnRefinedDict['orderedHash'][i]])

        with open(self.resultPath+self.fileName, 'w', encoding="utf-8") as r:
            for l in outputContent:
                r.write(l)

    def normalizeFile(self, smudgyFile, dupHashOverride=True, editFullwidthPunctuation=True) -> dict:
        localRawFile = smudgyFile.copy()
        newOriginDict = {'headerWords':[], 'orderedHash':[], 'content':[], 'duplicateHash':False, 'cotainStringsBlock':False, 'errorLog':{}}
        errorWords = [
            "You're using the 'dupHashOverride' mode, it will only keep the lastest updated content.",
            'All of the above are the dups you might want to clean from '+self.sourcePath+self.fileName,
            "Error, there are duplicate contents in this file and might cause malfunction(s) into renpy.",
            "The dups are from "+self.sourcePath+self.fileName,
            "Before cleaning them or choosing which line(s) to remain, the result is empty."
            ]

        temData = []
        currentHash = ""
        for line in localRawFile:
            if  self.findHashPattern in line:
                if currentHash == "":
                    newOriginDict['headerWords'] = temData
                else:
                    temData.insert(0, currentHash)
                    newOriginDict['content'].append({currentHash:temData})
                    newOriginDict['orderedHash'].append(currentHash)
                temData = []
                currentHash = line
            else:
                temData.append(line)
        temData.insert(0, currentHash)
        newOriginDict['content'].append({currentHash:temData})
        newOriginDict['orderedHash'].append(currentHash)
        temData = []

        while newOriginDict['orderedHash'].count(self.stringsBlockPattern) > 0:
            pos = newOriginDict['orderedHash'].index(self.stringsBlockPattern)
            temData.extend(newOriginDict['content'].pop(pos)[self.stringsBlockPattern][1:])
            newOriginDict['orderedHash'].pop(pos)
        if temData:
            temData.insert(0, self.stringsBlockPattern)
            newOriginDict['cotainStringsBlock'] = True
            newOriginDict['content'].append({self.stringsBlockPattern:temData})
            newOriginDict['orderedHash'].append(self.stringsBlockPattern)
        del temData
        del currentHash

        if len(newOriginDict['orderedHash']) != len(set(newOriginDict['orderedHash'])):
            dupHashMsg = str(set([str(newOriginDict['orderedHash'].count(hh))+'* '+hh[:-2] for hh in newOriginDict['orderedHash'] if newOriginDict['orderedHash'].count(hh)>1]))
            if dupHashOverride:
                for hh in newOriginDict['orderedHash'].copy():
                    while newOriginDict['orderedHash'].count(hh) > 1:
                        pos = newOriginDict['orderedHash'].index(hh)
                        newOriginDict['content'].pop(pos)
                        newOriginDict['orderedHash'].pop(pos)
                print(errorWords[0], dupHashMsg, errorWords[1], sep='\n')
            else:
                newOriginDict['duplicateHash'] = True
                print(errorWords[2], dupHashMsg, errorWords[3], errorWords[4], sep='\n')
                newOriginDict['headerWords'] = [errorWords[2]+'\n', dupHashMsg+'\n', errorWords[3]+'\n', errorWords[4]+'\n']
                newOriginDict['orderedHash'] = []
                newOriginDict['content'] = []

        if not newOriginDict['duplicateHash'] and editFullwidthPunctuation:
            for i in range(len(newOriginDict['orderedHash'])-1):
                newOriginDict['content'][i][newOriginDict['orderedHash'][i]] = self.editFuwiPunc(newOriginDict['content'][i][newOriginDict['orderedHash'][i]])
        return newOriginDict

    def editFuwiPunc(self, contentLines) -> list:
        # '!':'！', ':':'：', ',':':'、', are not easily replaced or fixed cuz of the syntax below, manually check ., '', [], $ and python code section please.
        # define earned_points_info = _("[points]{image=points.png} 贏得點數")
        # g "我很高興看到你 [earned_points_info!ti] "
        # $ percent = 100.0 * points / max_points
        # g "我百分之 [percent:.2] 喜歡你！"
        contentLines = contentLines.copy()
        targetPairs = {'...':'……',
            '-':'──',
            ',':'，',
            '．':'。',
            ':':'：',
            '!':'！',
            ':':'：',
            '?':'？'
        }
        hardToFind = {'..':'……',
        '.':'。',
        }
        mayDupPunc = ['…', '—', '─']

        nearestUpSideComment = []
        validLineCount = []
        addDoubleQuotes = False
        ncPos = -1

        for i in range(len(contentLines)):
            if not contentLines[i].isspace() and contentLines[i].lstrip().startswith('#') and '# TODO' not in contentLines[i] and '# game' not in contentLines[i]:
                nearestUpSideComment.append(i)
            if not contentLines[i].isspace() and not contentLines[i].lstrip().startswith('#') and '$ ' not in contentLines[i] and '[' not in contentLines[i] and self.findHashPattern not in contentLines[i]:
                validLineCount.append(i)
                for targ in targetPairs.keys():
                    contentLines[i] = contentLines[i].replace(targ, targetPairs[targ])

                contentLines[i] = contentLines[i].replace('..', hardToFind['..'])
                contentLines[i] = contentLines[i].replace('？？？', '???', 1)

                if '"' in contentLines[i]:
                    endPos = contentLines[i].rindex('"')
                    if contentLines[i][endPos-1] == '.':
                        contentLines[i] = contentLines[i][:endPos-1]+hardToFind['.']+contentLines[i][endPos:]

                for mdp in mayDupPunc:
                    contentLines[i] = self.findDupPunc(mdp, contentLines[i])

        if nearestUpSideComment and validLineCount:
            for nc in nearestUpSideComment:
                if nc < validLineCount[0]:
                    ncPos = nc

        if ncPos != -1:
            if '\\"' in contentLines[ncPos]:
                if contentLines[ncPos].index('\\"') != contentLines[ncPos].rindex('\\"'):
                    addDoubleQuotes = True

        if addDoubleQuotes:
            for valico in validLineCount:
                contentLines[valico] = self.addDoubQuo(contentLines[valico])
        return contentLines

    def findDupPunc(self, puncPattern, puncSourceLine) -> str:
        allMatches = [(m.start(0), m.end(0)) for m in re.finditer(puncPattern, puncSourceLine)]
        if allMatches:
            preMarked = ()
            singleMarks = []
            counter = 0
            tmplist = list(puncSourceLine)
            for p in allMatches:
                if not preMarked or counter == 2:
                    preMarked = p
                    counter = 1
                elif p[0] == preMarked[1] and counter < 2:
                    preMarked = p
                    counter += 1
                else:
                    singleMarks.append(preMarked)
                    preMarked = p
            if counter < 2:
                singleMarks.append(allMatches[-1])
            singleMarks.reverse()
            for sm in singleMarks:
                tmplist.insert(sm[1], puncPattern)

            return ''.join(tmplist)
        return puncSourceLine

    def addDoubQuo(self, addQuoteLine) -> str:
        if '“' in addQuoteLine  or '”' in addQuoteLine:
            tmplist = list(addQuoteLine)
            itsPos = []
            # insertPosOffset = False
            popCounter = ''.join(tmplist).count('\\"')
            for i in range(popCounter):
                popPos = ''.join(tmplist).index('\\"')
                itsPos.append(popPos+i)
                tmplist.pop(popPos)
                tmplist.pop(popPos)

            tmplist.reverse()

            while tmplist[tmplist.index('"')+1] == ' ' or tmplist[tmplist.index('"')+1] == '　':
                tmplist.pop(tmplist.index('"')+1)
            if tmplist[tmplist.index('"')+1] == '“' or tmplist[tmplist.index('"')+1] == '\\':
                tmplist[tmplist.index('"')+1] = '”'
            elif tmplist[tmplist.index('"')+1] != '”' and '”' not in tmplist:
                tmplist.insert(tmplist.index('"')+1, '”')

            tmpPopPos = tmplist.index('"')
            tmplist.pop(tmpPopPos)

            while tmplist[tmplist.index('"')-1] == ' ' or tmplist[tmplist.index('"')+1] == '　':
                tmplist.pop(tmplist.index('"')-1)
            if tmplist[tmplist.index('"')-1] == '”' or tmplist[tmplist.index('"')-1] == '\\':
                tmplist[tmplist.index('"')-1] = '“'
            elif tmplist[tmplist.index('"')-1] != '“' and '“' not in tmplist:
                tmplist.insert(tmplist.index('"'), '“')
                # insertPosOffset = True

            tmplist.insert(tmpPopPos, '"')
            tmplist.reverse()

            # if insertPosOffset:
            #     itsPos = [itps+1 for itps in itsPos]

            # for itps in itsPos:
            #     tmplist.insert(itps, '"')
            #     tmplist.insert(itps, '\\')

            addQuoteLine = ''.join(tmplist)
        else:
            if addQuoteLine.count('\\"'):
                if addQuoteLine.index('\\"') != addQuoteLine.rindex('\\"'):
                    addQuoteLine = addQuoteLine[:addQuoteLine.index('\\"')]+'“'+addQuoteLine[addQuoteLine.index('\\"')+2:addQuoteLine.rindex('\\"')]+'”'+addQuoteLine[addQuoteLine.rindex('\\"')+2:]
                else:
                    tmplist = list(addQuoteLine)
                    popPos = ''.join(tmplist).index('\\"')
                    tmplist.pop(popPos)
                    tmplist.pop(popPos)

                    tmplist.reverse()

                    while tmplist[tmplist.index('"')+1] == ' ' or tmplist[tmplist.index('"')+1] == '　':
                        tmplist.pop(tmplist.index('"')+1)
                    if tmplist[tmplist.index('"')+1] == '\\':
                        tmplist[tmplist.index('"')+1] = '”'
                    elif tmplist[tmplist.index('"')+1] != '”' and '”' not in tmplist:
                        tmplist.insert(tmplist.index('"')+1, '”')
                        # insertPosOffset = True

                    tmpPopPos = tmplist.index('"')
                    tmplist.pop(tmpPopPos)

                    while tmplist[tmplist.index('"')-1] == ' ' or tmplist[tmplist.index('"')+1] == '　':
                        tmplist.pop(tmplist.index('"')-1)
                    if tmplist[tmplist.index('"')-1] == '\\':
                        tmplist[tmplist.index('"')-1] = '“'
                    elif tmplist[tmplist.index('"')-1] != '“' and '“' not in tmplist:
                        tmplist.insert(tmplist.index('"'), '“')
                        # insertPosOffset = True

                    tmplist.insert(tmpPopPos, '"')
                    tmplist.reverse()

                    # if insertPosOffset:
                    #     popPos += 1
                    # tmplist.insert(popPos, '"')
                    # tmplist.insert(popPos, '\\')

                    addQuoteLine = ''.join(tmplist)
        return addQuoteLine

    def getLineContent(self, MTLine) -> str:
        tmplist = list(MTLine)
        itsPos = []
        popCounter = ''.join(tmplist).count('\\"')
        for i in range(popCounter):
            popPos = ''.join(tmplist).index('\\"')
            itsPos.append(popPos+i*2)
            tmplist.pop(popPos)
            tmplist.pop(popPos)

        tmplist.reverse()

        tmpPopEndPos = tmplist.index('"')
        tmplist.pop(tmpPopEndPos)
        tmpStartPos = tmplist.index('"')

        tmplist.insert(tmpPopEndPos, '"')
        correctStartPos = len(tmplist)-tmpStartPos-1
        correctEndtPos = len(tmplist)-tmpPopEndPos-1
        tmplist.reverse()

        for itps in itsPos:
            tmplist.insert(itps, '"')
            tmplist.insert(itps, '\\')
            correctEndtPos += 2

        return {'line':''.join(tmplist[correctStartPos:correctEndtPos]), 'startPos':correctStartPos}
