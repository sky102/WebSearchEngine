import json
import os
#from urllib.parse import urlparse

class Corpus:
    """
    This class is responsible for handling corpus related functionalities like mapping a url to its local file name
    """

    # The corpus directory name
    WEBPAGES_RAW_NAME = "WEBPAGES_RAW"
    # The corpus JSON mapping file
    JSON_FILE_NAME = os.path.join(".", WEBPAGES_RAW_NAME, "bookkeeping.json")
    #JSON_FILE_NAME = os.path.join(".", WEBPAGES_RAW_NAME, "bookkeeping_trunc.json")
    
    

    def __init__(self):
        self.file_url_map = json.load(open(self.JSON_FILE_NAME), encoding="utf-8")
        self.url_file_map = dict()
        for key in self.file_url_map:
            self.url_file_map[self.file_url_map[key]] = key
        
        try:
            self.id_title_map = json.load(open("doc_titles.json"), encoding="utf-8")
        except:
            #self._build_id_title_map()
            pass
        


    def get_file_name(self, url):
        """
        Given a url, this method looks up for a local file in the corpus and, if existed, returns the file address. Otherwise
        returns None
        """
        #url = url.strip()
        #parsed_url = urlparse(url)
        #url = url[len(parsed_url.scheme) + 3:]
        if url in self.url_file_map:
            addr = self.url_file_map[url].split("/")
            dir = addr[0]
            file = addr[1]
            return os.path.join(".", self.WEBPAGES_RAW_NAME, dir, file)
        return None
        
    def _build_id_title_map(self):
        from bs4 import BeautifulSoup
        self.id_title_map = dict()
        x = 0
        for k,url in self.file_url_map.items():
            try:
                soup = BeautifulSoup(open(self.get_file_name(url),'r',encoding='utf-8'),'html.parser')
                self.id_title_map[k] = soup.title.string
                #print(k,soup.title.string)
                
                if x == 1000:
                    try:
                        tmp = json.load(open("doc_titles.json"), encoding="utf-8")
                        self.id_title_map.update(tmp)
                    except:
                        pass
                    with open("doc_titles.json", 'w') as json_file:
                        json.dump(self.id_title_map, json_file)
                    x = 0
                    self.id_title_map = dict()
                else:
                    x += 1
            except:
                pass
