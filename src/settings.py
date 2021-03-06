#Scilens Directory
from pathlib import Path
scilens_dir = str(Path.home()) + '/Dropbox/scilens/'

#Use cached files
cache_dir = scilens_dir + 'cache/'

#Corpus files
glove_file = scilens_dir + 'big_files/glove.6B.300d.txt'



#Topic Discovery parameters
numOfTopics = 16
max_iter = 100


#Auxiliary Files
#File with refined topics
hn_vocabulary = open(scilens_dir + 'small_files/hn_vocabulary/hn_vocabulary.txt').read().splitlines()
#Predefined keyword lists
personKeywordsFile = scilens_dir + 'small_files/keywords/person.txt'
studyKeywordsFile = scilens_dir + 'small_files/keywords/study.txt'
actionsKeywordsFile = scilens_dir + 'small_files/keywords/action.txt'