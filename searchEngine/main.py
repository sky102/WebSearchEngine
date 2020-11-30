#import pymongo
import atexit
import os


from indexer import Indexer


#mongodb+srv://cs121se:<CS121%21%21%21>@cs121se-rlhbw.azure.mongodb.net/test?retryWrites=true

#ATLAS_CONNECTION = "mongodb+srv://cs121se:<CS121%21%21%21>@cs121se-rlhbw.azure.mongodb.net/test?retryWrites=true"

#WEBPAGES_RAW_NAME = "WEBPAGES_RAW"
#JSON_FILE_NAME = os.path.join(".", WEBPAGES_RAW_NAME, "bookkeeping.json")

if __name__ == '__main__':
    try:
        indexer = Indexer()
        atexit.register(indexer.save_indexer_progress)
        indexer.start()
        
    except:
        import traceback
        traceback.print_exc()