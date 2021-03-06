#!/usr/bin/env python

import os
import ConfigParser

class Config():
    def __init__(self, filePath):
        firstChr = filePath[:1]
        if firstChr == '.' or firstChr != '/':
            # Assume only file name
            dir = os.path.dirname(os.path.realpath(__file__))
            filePath = os.path.join(dir, filePath)
        self.filePath = filePath
        self.parser=ConfigParser.SafeConfigParser()
        self.parser.read([self.filePath])
        
    def getSections(self):
        return self.parser.sections()
    
    def doesSectionExist(self, section):
        found = False
        for s in self.getSections():
            if s == section:
                found = True
                break
        return found

    def getOptions(self, section):
        options = []
        if self.doesSectionExist(section):
            options = self.parser.items(section)
        return options

    def getValue(self, section, option):
        value = ''
        try:
            value = self.parser.getint(section, option)
        except ValueError:
            val = self.parser.get(section, option)
            if '\\n' in val:
                valueList = val.split('\\n')
                for v in valueList:
                    value += v + '\n'
            else:
                value = val
        return value
