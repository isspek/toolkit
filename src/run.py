from time import time
from diffusion_graph import create_graph
from graph_ops import download_articles, get_effective_documents, prune_graph, download_tweets, get_article_pairs
from settings import twitterCorpusFile, cache_dir
from matching import prepare_articles_matching, create_annotation_subsample, uniformly_random_subsample
from topic_detection import train_model, predict_topic

t0 = time()

#download_tweets(twitterCorpusFile, cache_dir + 'top_paper_3_tweets.txt', cache_dir + 'tweet_details_v1.tsv', 1)
#prepare_articles_matching(cache_dir + 'paper_details_v1.tsv', cache_dir + 'paper_details_v2.tsv')
#prepare_articles_matching(cache_dir + 'article_details_v1.tsv', cache_dir + 'article_details_v2.tsv')
#get_article_pairs('pruned_graph_v2.tsv', 'article_pairs.tsv')
#train_model(cache_dir + 'article_details_v2.tsv', cache_dir + 'paper_details_v2.tsv', cache_dir + 'topic_model')
#predict_topic(cache_dir + 'article_details_v2.tsv', cache_dir + 'article_details_v3.tsv', cache_dir + 'paper_details_v2.tsv', cache_dir + 'paper_details_v3.tsv', cache_dir + 'topic_model')
#create_annotation_subsample(diffusion_graph_dir+'article_pairs.tsv', cache_dir + 'article_details_v3.tsv', cache_dir + 'paper_details_v3.tsv', 1000, cache_dir + 'par_pairs_v1.tsv')
#uniformly_random_subsample(cache_dir + 'par_pairs_v1.tsv', 200, cache_dir + 'par_pairs_v2.tsv')

print("Total time: %0.3fs." % (time() - t0))
