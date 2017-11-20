from spacy.symbols import nsubj, dobj, VERB
from nltk.tokenize import sent_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation

from settings import *
from utils import *
from gloveEmbeddings import *

from pyspark.sql import SQLContext
from pyspark import SparkConf, SparkContext
if useSpark: ctx = SQLContext(SparkContext(conf = (SparkConf().setMaster('local[*]').setAppName('quoteExtraction').set('spark.executor.memory', '2G').set('spark.driver.memory', '40G').set('spark.driver.maxResultSize', '10G'))))

##Pipeline functions
def quotePipeline():
    documents = cachefunc(queryDB, ('web'))
    documents = cachefunc(extractQuotes, (documents))
    documents = cachefunc(removeQuotes, (documents))
    documents = cachefunc(discoverTopics, (documents))
    #documents = cachefunc(flattenQuotes, (documents))    
    return documents

def extractQuotes(documents):
    #concatenation of title and body
    documents['article'] = documents['title'] + '.\n ' + documents['body']
    documents = documents.drop(['title', 'body'], axis=1)

    #process articles to extract quotes
    if useSpark:
        rddd = ctx.createDataFrame(documents[['article']]).rdd
        documents['quotes'] = rddd.map(lambda s: dependencyGraphSearch(s.article)).collect()
    else:
        documents['quotes'] = documents['article'].map(dependencyGraphSearch)

    print('Dropping '+ str(np.count_nonzero(documents['quotes'].isnull())) + ' document(s) without quotes.')
    documents = documents.dropna()
    
    return documents

# Search for quote patterns
def dependencyGraphSearch(article):
        
    allPerEntities = []
    allOrgEntities = []
    for e in nlp(article).ents:
        if e.label_ == 'PERSON':
            allPerEntities.append(e.text)
        elif e.label_ == 'ORG':
            allOrgEntities.append(e.text)
            
    quotes = []

    for s in sent_tokenize(article):
        quoteFound = False
        quote = quotee = quoteeType = quoteeAffiliation = ""
        s = nlp(s)

        sPerEntities = []
        sOrgEntities = []
        for e in s.ents:
            if e.label_ == 'PERSON':
                sPerEntities.append(e.text)
            elif e.label_ == 'ORG':
                sOrgEntities.append(e.text)


        #find all verbs of the sentence.
        verbs = set()
        for v in s:
            if v.head.pos == VERB:
                verbs.add(v.head)

        if not verbs:
            continue

        rootVerb = ([w for w in s if w.head is w] or [None])[0]

        #check first the root verb and then the others.
        verbs = [rootVerb] + list(verbs)

        for v in verbs:
            if v.lemma_ in actionsKeywords:            

                quoteFound = True
                
                for np in v.children:
                    if np.dep == nsubj:
                        quotee = s[np.left_edge.i : np.right_edge.i+1].text
                        break

            if quoteFound:
                    quote = s.text.strip()
                    quotee, quoteeType, quoteeAffiliation = resolveQuotee(quotee, sPerEntities, sOrgEntities, allPerEntities, allOrgEntities)
                    quotes.append({'quote': quote, 'quotee':quotee, 'quoteeType':quoteeType, 'quoteeAffiliation':quoteeAffiliation})
                    break
    
    if quotes == []:
        return None
    else:
        return quotes

#Resolves the quotee of a quote.
def resolveQuotee(quotee, sPerEntities, sOrgEntities, allPerEntities, allOrgEntities):
    
    q = qtype = qaff = 'unknown'
    
    #case that quotee PER entity exists
    for e in sPerEntities:
        if e in quotee:
            q = e
            qtype = 'PERSON'
            
            #find affiliation of person
            for e in sOrgEntities:
                if e in quotee:
                    qaff = e
                    break
            
            #case where PERSON is referred to with his/her first or last name       
            if len(q.split()) == 1:
                for e in allPerEntities:
                    if q != e and q in e.split():
                        q = e
                        break
                        
            return (q, qtype, qaff)    

    #case that quotee ORG entity exists      
    for e in sOrgEntities:

        if e in quotee:
            q = e
            qtype = 'ORG'
            qaff = e
            
            #case where ORG is referred to with an acronym
            if len(q.split()) == 1:
                for e in allOrgEntities:
                    if q != e and len(e.split()) > 1:
                        fullAcronym = compactAcronym = upperAccronym = ''
                        for w in e.split():
                            for l in w:
                                if (l.isupper()):
                                    upperAccronym += l
                            if not nlp(w)[0].is_stop:
                                compactAcronym += w[0]
                            fullAcronym += w[0]

                        if q.lower() in [fullAcronym.lower(), compactAcronym.lower(), upperAccronym.lower()]:
                            q = e
                            qaff = e
                            break
       
            return (q, qtype, qaff)   
        
    #case that quotee entity doesn't exist
    try:
        noun = next(nlp(quotee).noun_chunks).root.lemma_
    except:    
        return (q, qtype, qaff)
    
    if noun in authorityKeywords:
        q = 'authority'
    elif noun in empiricalKeywords:
        q = 'empirical observation'
    return (q, qtype, qaff)


def removeQuotes(documents):
    
    if useSpark:
        rddd = ctx.createDataFrame(documents[['article', 'quotes']]).rdd
        documents['article'] = rddd.map(lambda s: removeQuotesFromArticle(s.article, s.quotes)).collect()
    else:
        documents['article'] = documents.apply(lambda x: removeQuotesFromArticle(x['article'], x['quotes'].copy()), axis=1)
    
    return documents

# Remove quotes from articles
def removeQuotesFromArticle(article, quotes):        
    articleWithoutQuotes = ''
    for s in nlp(article).sents:
        s = s.text.strip()
        if (quotes and s == quotes[0]['quote']):
            quotes.pop(0)
        else:
            articleWithoutQuotes += s + ' '
    return articleWithoutQuotes


def discoverTopics(documents):
    
    print(numOfTopics)
    #convert to tfidf vectors (1-2grams)
    tfidf_vectorizer = TfidfVectorizer(max_df=0.95, min_df=2, max_features=10000, stop_words='english', ngram_range=(1,2), token_pattern='\w+')
    tfidf = tfidf_vectorizer.fit_transform(documents['article'])

    #fit lda topic model
    lda = LatentDirichletAllocation(n_components=numOfTopics, max_iter=1024, learning_method='online', random_state=1, n_jobs=-1)
    lda.fit(tfidf)

    #get the names of the top features of each topic that form its label 
    feature_names = tfidf_vectorizer.get_feature_names()
    topiclabels = []
    for _, topic in enumerate(lda.components_):
        topiclabels.append(" ".join([feature_names[i] for i in topic.argsort()[:-topicTopfeatures - 1:-1]]))

    #add the topic label as a column in the dataFrame
    documents['topic_label'] = [topiclabels[t] for t in lda.transform(tfidf).argmax(axis=1)]

    print('Total number of topics:', len(documents.topic_label.unique()))
    print(documents.topic_label.unique())
    #discover the topic of each quote
    documents['quotes'].apply(lambda x: discoverQuoteTopic(x, tfidf_vectorizer, lda, topiclabels))

    #discover the topic of each quote
    #topics = documents.topic_label.unique()
    #tEmbeddings = topics2Vec(topics)
    #documents['quoteTopic'], documents['sim'] = zip(*documents['quote'].map(lambda x: findQuoteTopic(x, tEmbeddings)))
    return documents

def discoverQuoteTopic(quotes, tfidf_vectorizer, lda, topiclabels):
    quotesWithTopic = []
    for q in quotes:
        tfidf = tfidf_vectorizer.transform([q['quote']])
        print (topiclabels[lda.transform(tfidf).argmax(axis=1)[0]])
        
    return quotesWithTopic


#Discovers the most likely topic for a quote
def findQuoteTopic(quote, tEmbeddings):

    maxSim = 0.0
    topic = np.nan
    quoteVec = sent2Vec(quote)

    for t, vec in tEmbeddings.items():
        curSim = sim(quoteVec, vec)
        if curSim > maxSim:
            maxSim = curSim
            topic = t

    return topic, maxSim


def flattenQuotes(documents):
    documents = documents[['article', 'topic_label']].join(documents['quotes'].apply(pd.Series).stack().reset_index(level=1, drop=True).apply(pd.Series))    
    print('Total number of quotes:',human_format(documents.shape[0]))
    print ('Average number of quotes per Document:',len(documents)/limitDocuments)
    return documents
