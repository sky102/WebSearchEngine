import logging
import re
from urllib.parse import urlparse, parse_qs
from corpus import Corpus

from lxml import html
from collections import defaultdict
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

class Crawler:
    """
    This class is responsible for scraping urls from the next available link in frontier and adding the scraped links to
    the frontier
    """
    
    def __init__(self, frontier):
        self.frontier = frontier
        self.corpus = Corpus()
        
        self.subdomains = defaultdict(int)
        self.most_valid_links = (None,-1)
        self.downloaded_urls = set()
        self.traps = set()
        
        # list of all links ever added to the frontier, w/o scheme
        self.front = []
        # set of links that have already been parsed
        self.dup = set()
        
        # for comparing url similarities
        self.compare_url = None
        self.similar_url_count = 0
        self.compare_traps = set()

    def start_crawling(self):
        """
        This method starts the crawling process which is scraping urls from the next available link in frontier and adding
        the scraped links to the frontier
        """
        
        while self.frontier.has_next_url():
            url = self.frontier.get_next_url()
            if self.compare_url == None:
                self.compare_url = url
            logger.info("Fetching URL %s ... Fetched: %s, Queue size: %s", url, self.frontier.fetched, len(self.frontier))
            url_data = self.fetch_url(url)
            
            self.downloaded_urls.add(url)
            subdomain = urlparse(url).hostname.lower()
            if subdomain.startswith("www."):
                subdomain = subdomain[4:]
            self.subdomains[subdomain] += 1
            valid_links = set()
            
            for next_link in self.extract_next_links(url_data):
                parsed_link = urlparse(next_link)
                link = next_link[len(parsed_link.scheme)+3:] # url without scheme

                # if url is not a dup and is valid
                if not link in self.front and self.is_valid(next_link):
                    if self.corpus.get_file_name(next_link) is not None:
                        self.front.append(link)
                        self.frontier.add_url(next_link)
                        valid_links.add(next_link)
        
            # checks if url has more valid links than current most_valid_links
            if (len(valid_links) > self.most_valid_links[1]):
                self.most_valid_links = (url, len(valid_links))

        
        # write to analytics.txt here
        self.store_analytics()

    def fetch_url(self, url):
        """
        This method, using the given url, should find the corresponding file in the corpus and return a dictionary
        containing the url, content of the file in binary format and the content size in bytes
        :param url: the url to be fetched
        :return: a dictionary containing the url, content and the size of the content. If the url does not
        exist in the corpus, a dictionary with content set to None and size set to 0 can be returned.
        """
        url_data = {
            "url": url,
            "content": None,
            "size": 0
        }
        
        file_addr = self.corpus.get_file_name(url)
        if (file_addr is not None):
            file = open(file_addr, 'rb')
            url_data["content"] = file.read()
            file.close()
            url_data["size"] = len(url_data["content"])
            
        return url_data

    def extract_next_links(self, url_data):
        """
        The url_data coming from the fetch_url method will be given as a parameter to this method. url_data contains the
        fetched url, the url content in binary format, and the size of the content in bytes. This method should return a
        list of urls in their absolute form (some links in the content are relative and needs to be converted to the
        absolute form). Validation of links is done later via is_valid method. It is not required to remove duplicates
        that have already been fetched. The frontier takes care of that.

        Suggested library: lxml
        """
        outputLinks = []
        
        # document object model
        dom = html.fromstring(url_data["content"])
        # makes all links in the document absolute with the given root
        dom.make_links_absolute(url_data["url"])
        
        # iterlinks() yields (element, attribute, link, pos) for every link in the dom
        for ele,attr,link,pos in dom.iterlinks():
            outputLinks.append(link)
            
        return outputLinks

    def is_valid(self, url):
        """
        Function returns True or False based on whether the url has to be fetched or not. This is a great place to
        filter out crawler traps. Duplicated urls will be taken care of by frontier. You don't need to check for duplication
        in this method
        """
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
        try:
            is_trap = False
            # regex that catches directories repeating more than twice
            if (re.match("^.*?(?P<dir1>\/.+?\/).*?((?P=dir1).*){2,}$|^.*?\/(?P<dir2>.+?\/)((?P=dir2).*){2,}$", parsed.geturl().lower())):
                is_trap = True
            
            # url w/o the scheme
            stripped_url = url[len(parsed.scheme)+3:]
            
            # if the url is not a duplicate
            if not stripped_url in self.dup:
                
                if (parsed.query != '' and any([SequenceMatcher(None, trap_url, url).ratio() > 0.65 for trap_url in self.compare_traps])):
                    is_trap = True
                else:
                    # if the url has queries and is similar to the previous url added to the frontier
                    if parsed.query != '' and SequenceMatcher(None, self.compare_url, url).ratio() > 0.65:
                        self.similar_url_count += 1
                    else:
                        self.similar_url_count = 0

                    if self.similar_url_count > 35: # if there are too many similar urls in a row, flag as a trap
                        is_trap = True
                        self.compare_traps.add(url)
            
            # add url to duplicates set
            self.dup.add(stripped_url)
            
            # if the url is a trap and is in the file system, add it as a trap
            if is_trap:
                if self.corpus.get_file_name(url) is not None:
                    self.traps.add(url)
                return False
            
            valid =  ".ics.uci.edu" in parsed.hostname \
                   and not re.match(".*\.(css|js|bmp|gif|jpe?g|ico" + "|png|tiff?|mid|mp2|mp3|mp4" \
                                    + "|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf" \
                                    + "|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso|epub|dll|cnf|tgz|sha1" \
                                    + "|thmx|mso|arff|rtf|jar|csv" \
                                    + "|rm|smil|wmv|swf|wma|zip|rar|gz|pdf)$", parsed.path.lower())
            
            # if the url is not a trap and is valid, set it as the new url to compare against
            if not is_trap and valid:
                self.compare_url = url
            
            return valid
                   
                   # **REGULAR EXPRESSION ADAPTED FROM (^.*?(\/.+?\/).*?\1.*$|^.*?\/(.+?\/)\2.*$):
                   # https://support.archive-it.org/hc/en-us/articles/208332963-Modify-your-crawl-scope-with-a-Regular-Expression
        
        except TypeError:
            print("TypeError for ", parsed)
            return False
            
    def store_analytics(self):
        sbdm = "" #subdomains
        for s,i in self.subdomains.items():
            sbdm += s + " \t-> " + str(i) + '\n'
        
        dwnld = "\n".join(sorted(self.downloaded_urls)) #downloaded urls
        trp = "\n".join(sorted(self.traps)) #traps
        
        file = open("analytics.txt", "w+")
        file.write("Subdomains: \n" + sbdm)
        file.write("\nMost valid outlinks: \n" + str(self.most_valid_links))
        file.write("\n\nDownloaded URLs: \n" + dwnld)
        file.write("\n\nTraps: \n" + trp)
        file.close()
        
        #file = open("frontier.txt", "w+")
        #file.write("\n".join(self.front))
        #file.close()
        

