from bs4 import BeautifulSoup
from urllib.request import Request, build_opener, HTTPCookieProcessor
from urllib.parse import urlencode
from http.cookiejar import MozillaCookieJar
import re, time, sys, urllib
import matplotlib.pyplot as plt
import concurrent.futures
import pandas as pd
import itertools
import requests
import string
import json
import time


def get_num_results(keyword, start_year, end_year):

    # Reading the html of webpage
    user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.109 Safari/537.36'
    query_params = { 'q' : keyword, 'as_ylo' : start_year, 'as_yhi' : end_year}
    url = "https://scholar.google.com/scholar?as_vis=1&hl=en&as_sdt=1,5&" + urllib.parse.urlencode(query_params)
    opener = build_opener()
    request = Request(url=url, headers={'User-Agent': user_agent})
    handler = opener.open(request)
    html = handler.read() 

    # Parsing html with soup
    soup = BeautifulSoup(html, 'html.parser')

    # find line 'About x results (y sec)
    div_results = soup.find("div", {"id": "gs_ab_md"}) 

    if div_results != None:

        res = re.findall(r'(\d+).?(\d+)?.?(\d+)?\s', div_results.text) 
        
        if res == []:
            num_results = '0'
            success = True
        else:
            num_results = ''.join(res[0])
            success = True

    else:
        success = False
        num_results = 0

    return num_results, success

def get_range(keyword, start_year, end_year):

    fp = open("count_keyword_"+keyword+".csv", 'w')
    fp.write("year,results\n")
    print("year,results")

    years = []
    results = []
    for year in range(start_year, end_year + 1):
        
        years.append(year)
        num_results, success = get_num_results(keyword, year, year)
        if not(success):
            print("Error while fetching from GScholar.")
            break
        year_results = "{0},{1}".format(year, num_results)
        print(year_results)
        results.append(year_results)
        fp.write(year_results + '\n')
        time.sleep(0.8)

    fp.close()
    return years, results

'''
These methods will allow finding other keywords relevant to a given keyword, we 
make use of GScholar's autocomplete and suggestions feature
'''
startTime = time.time()

# If you use more than 50 seed keywords you should slow down your requests - otherwise google is blocking the script
# If you have thousands of seed keywords use e.g. WAIT_TIME = 1 and MAX_WORKERS = 10

WAIT_TIME = 0.1
MAX_WORKERS = 20

# set the autocomplete language
lang = "en"


charList = " " + string.ascii_lowercase + string.digits

def makeGoogleRequest(query):
    # If you make requests too quickly, you may be blocked by google 
    time.sleep(WAIT_TIME)
    
    URL="https://scholar.google.com/scholar_complete"
    PARAMS = {"client": "opera",
        "hl": lang,
        "q": query}
    
    headers = {'User-agent':'Mozilla/5.0'}
    response = requests.get(URL, params=PARAMS, headers=headers)
    if response.status_code == 200:
        try:
            suggestedSearches = json.loads(response.content.decode('utf-8'))["l"]
        except:
            suggestedSearches = json.loads(response.content.decode('latin-1'))["l"]
        return suggestedSearches
    else:
        return "ERR"


def getGoogleSuggests(keyword):
    # err_count1 = 0
    queryList = [keyword + " " + char for char in charList]
    suggestions = []
    for query in queryList:
        suggestion = makeGoogleRequest(query)
        if suggestion != 'ERR':
            suggestions.append(suggestion)

    # Remove empty suggestions
    suggestions = set(itertools.chain(*suggestions))
    if "" in suggestions:
        suggestions.remove("")

    return suggestions

def launchSuggestion():
    #read your csv file that contain keywords that you want to send to google scholar autocomplete
    df = pd.read_csv("keyword_seeds.csv")
    # Take values of first column as keywords
    keywords = df.iloc[:,0].tolist()

    resultList = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futuresGoogle = {executor.submit(getGoogleSuggests, keyword): keyword for keyword in keywords}

        for future in concurrent.futures.as_completed(futuresGoogle):
            key = futuresGoogle[future]
            for suggestion in future.result():
                resultList.append([key, suggestion])

    # Convert the results to a dataframe
    outputDf = pd.DataFrame(resultList, columns=['Keyword','Suggestion'])

    # Save dataframe as a CSV file
    outputDf.to_csv('keyword_suggestions.csv', index=False)
    print('keyword_suggestions.csv File Saved')

    print(f"Execution time: { ( time.time() - startTime ) :.2f} sec")


if __name__ == "__main__":

    if len(sys.argv) < 3:
        print("Usage: python keyword_count.py '<keyword1>' <start year> <end year>" "[1]" "1 is optional to enable autosuggest")
        
        
    else:
        keyword = sys.argv[1]
        start_year = int(sys.argv[2])
        end_year = int(sys.argv[3])
        years, results = get_range(keyword, start_year, end_year)

        if(sys.argv[4]):
            launchSuggestion()
        
        plt.plot(years, results)
 
        plt.title('Classes by Date')
 
 
        plt.xlabel('Date')
        plt.ylabel('Classes')
        plt.show()

    