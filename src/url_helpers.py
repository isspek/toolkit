import re
from urllib.parse import urlsplit
from urllib.request import urlopen

import pandas as pd
import requests
from bs4 import BeautifulSoup

from settings import *


#Download papers
def download_selected_papers():
    with open(selected_papers_file) as f:
        selected_papers = f.readlines()
    
    for id, p in enumerate(selected_papers):
        try:  
            links = get_html(p).findAll('a')
        except:
            print('Manual checking:', p)
            continue

        pdfs = []
        for l in links:
            try:
                if l['href'][-4:]=='.pdf':
                    pdfs.append(l)
            except:
                continue

        if len(pdfs)==0:
            print('[no pdfs] Manual checking:', p)
            continue

        if len(pdfs)>1:
            print('[many pdfs] Manual checking:', p)
            continue
                
        with open('cache/'+str(id)+'.pdf','wb') as output:
            output.write(urlopen(pdfs[0]).read())


#Find the domain and the path of an http url
def analyze_url(url):
    try:
        url=urlsplit(url)
        domain = re.sub(r'^(http(s)?://)?(www\.)?', r'', url.netloc)
        path = '' if domain == '' else url.path

        return domain, path
    except:
        return url, ''

#Compare two domains
def same_domains(domain_1, domain_2):
    if domain_1.count('.') == 2:
        domain_1 = ('.').join(domain_1.split('.')[1:])
    if domain_2.count('.') == 2:
        domain_2 = ('.').join(domain_2.split('.')[1:])
    
    if domain_1 in domain_2 or domain_2 in domain_1:
        return True
    return False

#Resolve short url
def resolve_short_url(url):
    if url=='':
        return graph_nodes['tweetWithoutURL']
        
    try:
        #Follow the redirections of a URL
        r = requests.head(url, allow_redirects='HEAD', timeout=url_timeout)
        if r.status_code != 403:            
            r.raise_for_status()

        #Avoid blacklisted and flat URLs
        domain, path = analyze_url(r.url)
        if domain in blacklistURLs or path in ['', '/']:
            r.url = ''

        return r.url

    #Catch the different errors       
    except requests.HTTPError as e:
        return graph_nodes['HTTPError']
    except:
        return graph_nodes['TimeoutError']

#scrap html page as a browser
def get_html(url):
	headers = {"User-Agent":"Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11"}
	r = requests.get(url, allow_redirects='HEAD', timeout=url_timeout, headers=headers)
	return BeautifulSoup(r.content, 'html.parser', from_encoding="iso-8859-1")

#scrap CWUR World University Rankings
def scrap_cwur():
	for year in ['2017']:

	    soup = BeautifulSoup(urlopen('http://cwur.org/'+year+'.php'), 'html.parser')
	    table = soup.find('table', attrs={'class' : 'table'})

	    headers = ['URL']+[header.text for header in table.find_all('th')]+['Year']

	    rows = []

	    for row in table.find_all('tr')[1:]:
	        soup = BeautifulSoup(urlopen('http://cwur.org'+row.find('a')['href'][2:]), 'html.parser')
	        url = soup.find('table', attrs={'class' : 'table table-bordered table-hover'}).find_all('td')[-1].text
	        rows.append([url]+[val.text for val in row.find_all('td')]+[year])

	    df = pd.DataFrame(rows, columns = headers)
	    df = df.applymap(lambda x: x.strip('+')).drop('World Rank', axis=1).reset_index().rename(columns={'index':'World Rank'})

	    df.to_csv(institutionsFile, sep='\t', index=False)


#scrap nutritionfacts.org topics
def scrap_nutritionfacts():
    soup = BeautifulSoup(urlopen('https://nutritionfacts.org/topics'), 'html.parser')
    div = soup.find('div', attrs={'class' : 'topics-index'})

    with open(topicsFile, 'w') as f:
    	for t in div.find_all('a', title=True):
    		f.write(t['title'] + '\n')
