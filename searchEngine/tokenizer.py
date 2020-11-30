#Updated: 5/26/2019 18:21
#import regex as re
#re.DEFAULT_VERSION = re.VERSION1
from lxml import html
from bs4 import BeautifulSoup
from collections import defaultdict
from nltk import word_tokenize
import nltk
#nltk.download('stopwords')
from nltk.stem import PorterStemmer
from nltk.stem.wordnet import WordNetLemmatizer
# -*- coding: utf-8 -*-
from nltk.corpus import stopwords

class Tokenizer:
    """
    This class takes a file as argument and process the document. It will return a dictionary in the format
    {token:frequency}.
    """
    def __init__(self):
        self.theDict = defaultdict(int)
        self.englishWords = set(nltk.corpus.words.words())
        self.stop_words = set(stopwords.words('english'))
    """
    This method takes a file as an argument and extract text from the title and body of the file. It will then return 
    a dictionary contains the uniqe words and their frequencies.
    """
    def wordsTokenize(self, aFileAddr):
        self.theDict = defaultdict(int)
        ### Trying with BeautifulSoup
        # Opening the file and process it with Beautiful Soup
        file = open(aFileAddr, 'r', encoding='utf-8')
        contents = file.read()
        soup = BeautifulSoup(contents, 'lxml')
        self.cleanSoup(soup)
        # self.testSoup(soup)

        try:
            self.processFile(soup.get_text())
        except:
            raise
        # try:
        #     self.processFile(soup.body.text)
        # except:
        #     pass

        return self.theDict

    def processFile(self, aFile):
        tokens = word_tokenize(aFile.lower())
        self.processTokens(tokens)

    # Updated: 5/26/2019 17:00
    def processTokens(self, words):
        words = self.removeStopWords(words)
        ps = PorterStemmer()
        for word in words:
            word = ps.stem(word)
            if self.isEnglish(word) and word.isalpha() and len(word) > 1:
                self.theDict[word] += 1

    # def processTokens_Lem(self, words):
    #     lem = WordNetLemmatizer()
    #     for word in words:
    #         word = lem.lemmatize(word)
    #         if word.isalpha():
    #             self.theDict[word] += 1

    def cleanSoup(self, html):
        for script in html(["script", "style"]):
            script.extract()

    # Updated: 5/26/2019 17:00
    # This method detects if there's non-English characters in a word. It returns True if the word is only consisted of
    # English characters, False otherwise. This method was learned from this url: https://stackoverflow.com/questions/27084617/detect-strings-with-non-english-characters-in-python
    def isEnglish(self, aWord):
        try:
            aWord.encode(encoding='utf-8').decode('ascii')
        except UnicodeDecodeError:
            return False
        else:
            return True

    # Updated: 5/26/2019
    # This method takes a list of tokens and returns a new list in which the stop words are removed.
    def removeStopWords(self, words):
        filteredList = [w for w in words if not w in self.stop_words]
        return filteredList

    def testSoup(self, html):
        print('Before cleanning: ', html.prettify())
        self.cleanSoup(html)
        print('After cleanning: ', html.prettify())