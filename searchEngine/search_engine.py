import tkinter as tk
#from tkinter import ttk
import webbrowser

import pymongo
from pymongo import MongoClient
from bs4 import BeautifulSoup
from nltk.stem import PorterStemmer
from nltk import word_tokenize
import re

from corpus import Corpus
import json

from collections import defaultdict
import math
from sklearn.metrics.pairwise import cosine_similarity

WINDOW_WIDTH = 600
WINDOW_HEIGHT = 550

class FilePage:
    """
    This class creates a tkinter window that displays the given file.
    """
    def __init__(self, file, link=None):
        self.root = tk.Tk()
        self.file = file
        if link == None:
            link = str(file)
        self.root.title(link)
        self.root.minsize(width = WINDOW_WIDTH, height = WINDOW_HEIGHT)
        self.root.rowconfigure(0, weight = 1)
        self.root.columnconfigure(0, weight = 1)
        
        self.create_widgets()
    
    def create_widgets(self):
        self.display = tk.Text(self.root, wrap=tk.NONE)
        self.display.grid(row=0, column=0, sticky='nesw')
        
        self.Yscrollbar = tk.Scrollbar(self.display, orient=tk.VERTICAL, cursor='')
        self.Yscrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.display.config(yscrollcommand=self.Yscrollbar.set)
        self.Yscrollbar['command'] = self.display.yview
        
        self.Xscrollbar = tk.Scrollbar(self.display, orient=tk.HORIZONTAL)
        self.Xscrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.display.config(xscrollcommand=self.Xscrollbar.set)
        self.Xscrollbar['command'] = self.display.xview
        
    def open(self):
        file = open(self.file, 'r', encoding='utf-8')
        data = file.read()
        file.close()
        
        soup = BeautifulSoup(data, 'html.parser')
        for script in soup(["script", "style"]):
            script.extract()
        text = soup.get_text()
        
        self.display.insert(tk.END, text)
        self.display['state'] = tk.DISABLED
        self.root.mainloop()

class SearchEngine:
    """
    This search engine class searchs and ranks documents in the database
    based on the given user query, and returns a list of urls.
    """
    def __init__(self):
        self.client = MongoClient("mongodb+srv://cs121se:cs121@cs121se-rlhbw.azure.mongodb.net/test?retryWrites=true") 
        self.database = self.client["SearchEngine"]
        #self.collection = self.database["InvertedIndex"]
        self.collection = self.database["Index"]
        
        self.PS = PorterStemmer()
    
    def search(self, query):
        '''Returns a list of doc ids based on given query'''
        # try:
            # results = set()
            # for q in query.split():
                # database_results = self.collection.find_one({"term": self.PS.stem(q)})
                # if (results == set()):
                    # results = set([d['doc'] for d in database_results["post"]])
                # else:
                    # results = results & set([d['doc'] for d in database_results["post"]])
            
        # except:
            # results = []
        # return list(results)
        
        query = [self.PS.stem(q) for q in query.split()]
        
        results = defaultdict(dict)
        query_tfidf = dict()
            
        for q in set(query):
            postings = self._query_database(q)
            
            if postings != None:
                query_tfidf[q] = (1 + math.log10(query.count(q))) * math.log10(37497/len(postings["post"]))
                
                for id,tf in postings["post"].items():
                    df = len(postings["post"])
                    tfidf = (1 + math.log10(tf)) * math.log10(37497/df)
                    results[id][q] = tfidf
            else:
                query_tfidf[q] = 0
        
        score = dict()
        for doc,tfidf in results.items():
            score[doc] = self._cosine_similarity(query_tfidf, tfidf)[0][0]
        
        top_twenty_results = []
        k = 0
        #for doc,_ in sorted(results.items(), key=lambda x: -x[1]):
        for doc,_ in sorted(score.items(), key=lambda x: -x[1]):
          #print(_,doc)
          top_twenty_results.append(doc)
          k += 1
          if k == 20:
              return top_twenty_results
        return top_twenty_results
    
    def _cosine_similarity(self, query, doc):
        q_array = []
        d_array = []
        for q,score in query.items():
            q_array.append(score)
            try:
                d_array.append(doc[q])
            except:
                d_array.append(0)
        return cosine_similarity([q_array],[d_array])
    
    def _query_database(self, query):
        return self.collection.find_one({"_id": query})

class SearchEngineGUI:
    """
    This class creates a tkinter GUI for the search engine.
    """
    def __init__(self, search_engine):
        self.corpus = Corpus()
        self._search_engine = search_engine
        
        self.root = tk.Tk()
        self.root.title("INF141/CS121: Information Retrieval - Project3: Search Engine")
        self.root.minsize(width = WINDOW_WIDTH, height = WINDOW_HEIGHT)
        #self.root.maxsize(width = WINDOW_WIDTH, height = WINDOW_HEIGHT)
        
        self.configure_grid()
        self.create_widgets()
        
        self.user_query = ''
        self.search_results = []
    
    def mainloop(self):
        self.root.mainloop()
    
    def configure_grid(self):
        '''Configures the tkinter root frame'''
        for i in range(1,9):
            self.root.rowconfigure(i, weight = 1)
        self.root.columnconfigure(0, weight = 10)
        #self.root.columnconfigure(1, weight = 1)
        self.root.columnconfigure(2, weight = 1)
    
    def create_widgets(self):
        '''Creates GUI tkinter widgets'''
        self.query_entry = tk.Entry(self.root)
        self.query_entry.grid(row=0,column=0, columnspan=2, sticky='ew')
        self.query_entry.bind('<Return>', self._search)
        self.query_entry.focus()
        
        self.search_button = tk.Button(self.root, text="SEARCH", command=self._search, bg="cornflower blue")
        self.search_button.grid(row=0,column=2, sticky='ew')
        
        self.resultsBox = tk.Listbox(self.root)
        self.resultsBox.grid(column=0, columnspan=3, row=1, rowspan=5, sticky='nesw')
        self.resultsBox.bind('<Return>', self._open)
        self.resultsBox.bind('<<ListboxSelect>>', self._get_descr)
        self.resultsBox.bind('<Double-Button-1>', self._open)
        self.query_entry.bind('<Down>', lambda event: self.resultsBox.focus())
        
        self.scrollbar = tk.Scrollbar(self.resultsBox, orient=tk.VERTICAL)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.resultsBox.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar['command'] = self.resultsBox.yview
        
        self.descriptionFrame = tk.Frame(self.root)
        self.descriptionFrame.grid(row=6,rowspan=3,column=0,columnspan=3,sticky='nesw')
        self.descriptionFrame.rowconfigure(0, weight = 1)
        self.descriptionFrame.columnconfigure(0, weight = 1)
        self.descriptionFrame.grid_propagate(False)
        self.description = tk.Text(self.descriptionFrame,height=9,state=tk.DISABLED)
        self.description.grid(row=0,column=0)
        self.description.tag_config("underline", underline=1)
        self.description.tag_config("query", background="yellow")
        
        self.in_browser = tk.IntVar()
        self.in_browser_check = tk.Checkbutton(self.root, text='in browser', variable=self.in_browser)
        self.in_browser_check.grid(row=9,column=1)
        
        self.open_button = tk.Button(self.root, text="OPEN", command=self._open, bg="pale goldenrod")
        self.open_button.grid(row=9,column=0, sticky='ew')
        self.cancel_button = tk.Button(self.root, text="CANCEL", command=self._cancel, bg="light coral")
        self.cancel_button.grid(row=9,column=2, sticky='ew')
        
    def _search(self, event=None):
        '''Gives user query to the search engine and displays results'''
        self.user_query = self.query_entry.get().strip().lower()
        if self.user_query == '':
            return
        
        self._clear_search()
        #self.search_results = [self.corpus.file_url_map[d['_id']] for d in self._search_engine.search(self.user_query)]
        self.search_results = [self.corpus.file_url_map[id] for id in self._search_engine.search(self.user_query)]
        
        
        for s in self.search_results:
            try:
                self.resultsBox.insert(tk.END, self.corpus.id_title_map[self.corpus.url_file_map[s]]+" -- "+s)
            except:
                self.resultsBox.insert(tk.END, s)
        
        #print("# of results:", len(self.search_results))
        #for s in self.search_results[0:20]:
        #    print(s)
        
        
    def _get_descr(self, event=None):
        '''Inserts selected page/url title and preview into description box'''
        selected_index = self.resultsBox.curselection()
        if selected_index == tuple():
            return
        
        url = self.search_results[selected_index[0]]
        file = open(self.corpus.get_file_name(url), 'r', encoding="utf-8")
        data = file.read()
        file.close()
        
        soup = BeautifulSoup(data, 'lxml')
        
        self.description['state'] = tk.NORMAL
        self.description.delete('1.0',tk.END)
        
        try:
            title = soup.title.string + '\n\n'
            self.description.insert(tk.END, title, "underline")
        except:
            pass
        
        query_list = self.user_query.split()
        
        for script in soup(["script", "style"]):
            script.extract()
        
        text = soup.get_text().split()
        text_stem = [self._search_engine.PS.stem(s.lower()) for s in text]
        for q in query_list:
            found = True
            try:
                index = text_stem.index(self._search_engine.PS.stem(q))
            except:
                try:
                    for i in range(len(text)):
                        p = "([A-Za-z]+"+q+")|("+q+"[A-Za-z]+)"
                        s = self._search_engine.PS.stem(q)
                        word = text[i].lower()
                        if (q in word and not re.search(p,word)):
                            index = i;
                            break;
                        else:
                            if not re.search("[A-Za-z]+"+s,word):
                                match = re.search(s+"[A-Za-z]*",word)
                                if match:
                                    if self._search_engine.PS.stem(word[match.span()[0]:match.span()[1]]) == s:
                                        index = i;
                                        break;
                except:
                    found = False
            finally:
                if found:
                    try:
                        desc = '...'
                        desc += " ".join(text[max(index-20,0):index])
                        self.description.insert(tk.END, desc+" ")
                        self.description.insert(tk.END, text[index], "query")
                        desc = " ".join(text[index+1:min(index+20,len(text))])
                        desc += '...\n'
                        self.description.insert(tk.END, " "+desc)
                    except:
                        pass
        
        self.description['state'] = tk.DISABLED
    
    def _open(self, event=None):
        '''Opens the selected page/url'''
        selected_index = self.resultsBox.curselection()
        if selected_index == tuple():
            return
        
        url = self.search_results[selected_index[0]]
        
        if (self.in_browser.get()):
            webbrowser.open(url, new=2)
        else:
            page = FilePage(self.corpus.get_file_name(url), link=url)
            page.open()
    
    def _cancel(self):
        '''Cancels and resets the search engine and GUI'''
        self.user_query = ''
        self.query_entry.delete(0, tk.END)
        self.query_entry.focus()
        self._clear_search()
        
    def _clear_search(self):
        '''Clears the searchbox'''
        self.resultsBox.delete(0, tk.END)
        self.search_results = []
        self.description['state'] = tk.NORMAL
        self.description.delete('1.0',tk.END)
        self.description['state'] = tk.DISABLED
        

if __name__ == "__main__":
    try:
        search_engine = SearchEngine()
        search_engine_gui = SearchEngineGUI(search_engine)
        search_engine_gui.mainloop()
    except:
        import traceback
        traceback.print_exc()