from corpus import Corpus
from tokenizer import Tokenizer
from collections import defaultdict
import pymongo
from pymongo import MongoClient
import json
from pprint import pprint

import math

import os
import pickle


class Indexer:

    BLOCK_SIZE = 1000 # 100? 500?
    
    INDEXER_DIR_NAME = "indexer_state"
    INDEXED_FILE_NAME = os.path.join(".", INDEXER_DIR_NAME, "indexed.pkl")
    
    def __init__(self):
        self.corpus = Corpus()
        self.tokenizer = Tokenizer()
        
        #self.block_index = defaultdict(list)
        self.block_index = defaultdict(dict)
        # host, port; client = MongoClient() connects to default host/port
        self.client = MongoClient("mongodb+srv://cs121se:cs121@cs121se-rlhbw.azure.mongodb.net/test?retryWrites=true") 
        # our database
        self.database = self.client["SearchEngine"]
        self.collection = self.database["Index"]
        #self.collection = self.database["test2"]
        #self.collection.create_index([("term", pymongo.ASCENDING)])
        
        self.indexed = set()

    def start(self):
        self.load_indexer_progress()
        block = 0
        temp_indexed = set()
        for url,id in self.corpus.url_file_map.items():
            if not url in self.indexed:# and not url== "mondego.ics.uci.edu/datasets/maven-contents.txt":
                if block >= self.BLOCK_SIZE:
                    block = 0
                    # store self.block_index in database
                    # clear self.block_index
                    self.store_in_database(temp_indexed)
                    temp_indexed = set()
                
                print(block,"- tokenizing:", url)
                try:
                    d = self.tokenizer.wordsTokenize(self.corpus.get_file_name(url))
                except:
                    print(self.corpus.get_file_name(url), "raised error")
                    raise
                temp_indexed.add(url)
                for t,tf in d.items():
                    #self.block_index[t].append({'doc':id,'freq':tf})
                    self.block_index[t][id] = tf
                block += 1
        
        self.store_in_database(temp_indexed)
        
        print ("INDEXING COMPLETE")
        # prints all docs in collection
        #docs = self.collection.find({})
        #for doc in docs: 
        #    pprint(doc)
        #print(self.block_index)
        
    
    def store_in_database(self, temp_indexed):
       # How to update a document:
       # https://www.guru99.com/mongodb-update-document.html
       # https://docs.mongodb.com/manual/reference/method/db.collection.update/
       # If upsert = true, create new doc when no doc matches query criteria
       # default = false, new doc is not inserted when no match is found
       
       # for every token, check if it is in database already
       # if self.collection.find_one({"term":t}) != None:
        #self.collection.update_one({"term":t}, {"$set": {"post": {"doc": id, "freq": tf}}}, upsert=True)
       # update if it is, insert if it is not
      #  else:
      #      posting = {"term":t, "doc_id":id, "freq": tf}
      #      self.collection.insert_one(posting)
      
      # Can insert an array of documents: 
      # https://www.tutorialspoint.com/mongodb/mongodb_insert_document.htm
      # Tried to add all doc ids first and update by term query but only getting 52/456 after breaking something
      
      count = len(self.block_index)
      print("storing in database:", count, "tokens.")
      n = 1
      
      for t,d in self.block_index.items():
        print("\t",n,"/",count,"- storing", t, "in database")
        docs = self.collection.find_one({"_id":t})
        if docs == None:
            self.collection.insert_one({"_id":t, "post":d})
            #self.collection.insert_one({"term":t, "post": []})
        else:
            docs = docs["post"]
            docs.update(d)
            self.collection.update_one({"_id":t}, {"$set": {"post":docs}})
        #self.collection.update_one({"term":t}, {"$push": {"post": {"$each": docs}}}, upsert=True)
        n += 1
        
      self.block_index = defaultdict(dict)
      self.indexed = self.indexed | temp_indexed
    
    def save_indexer_progress(self):
        if not os.path.exists(self.INDEXER_DIR_NAME):
            os.makedirs(self.INDEXER_DIR_NAME)

        indexed_file = open(self.INDEXED_FILE_NAME, "wb")
        pickle.dump(self.indexed, indexed_file)
        
        import datetime
        print("\tSaved at", datetime.datetime.now())
        
    def load_indexer_progress(self):
        if os.path.isfile(self.INDEXED_FILE_NAME):
            try:
                self.indexed = pickle.load(open(self.INDEXED_FILE_NAME, "rb"))
                print("loaded indexer state.", len(self.indexed),"urls")
            except:
                pass
