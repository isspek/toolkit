import networkx as nx
import pandas as pd

from diffusion_graph import create_graph
from settings import *
from url_helpers import analyze_url

#prune the initial diffusion graph by keeping only the paths that contain the selected papers
def prune_graph(papersFile):

    if not useCache or not os.path.exists(diffusion_graph_dir+'pruned_graph.tsv'):
        G = create_graph()

        df = pd.read_csv(diffusion_graph_dir+'epoch_0.tsv', sep='\t').dropna()
        df['social'] = project_url+'#twitter'
        G =  nx.compose(G, nx.from_pandas_edgelist(df, source='social', target='source_url', create_using=nx.DiGraph()))

        papers = open(papersFile).read().splitlines()

        newG = nx.DiGraph()
        for path in nx.all_simple_paths(G, source=project_url+'#twitter', target=project_url+'#source'):
            for paper in papers:
                if paper in path:
                    for i in range(1, len(path)):
                        newG.add_edge(path[i-1], path[i])

        print(len([s for s in newG.successors(project_url+'#twitter')]), 'tweets out of', len(newG.nodes), 'nodes')
    
        with open(diffusion_graph_dir+'pruned_graph.tsv', 'w') as f:
            for edge in newG.edges:
                    f.write(edge[0] + '\t' + edge[1] + '\n')

    G = nx.DiGraph()
    edges = open(diffusion_graph_dir+'pruned_graph.tsv').read().splitlines()
    for e in edges:
        [e0, e1] = e.split()
        G.add_edge(e0, e1)

    return G

#get selected papers
def get_most_widely_referenced_publications(different_domains, filename):
    G = create_graph()

    pubs = []
    for r in G.predecessors(project_url+'#repository'):
        for n in G.predecessors(r):
            domains = set()
            for w in G.predecessors(n):
                domain, _ = analyze_url(w)
                domains.add(domain)
            pubs.append([n, len(domains)])
    pubs = pd.DataFrame(pubs)
    pubs = pubs.sort_values(1, ascending=False)

    pubs[pubs[1]>=different_domains][0].to_csv(filename, index=False)

#(Deprecated)
def get_most_popular_publications(filename):
    G = create_graph()
    
    df = pd.read_csv(diffusion_graph_dir+'epoch_0.tsv', sep='\t').dropna()
    df['social'] = project_url+'#twitter'
    G =  nx.compose(G, nx.from_pandas_edgelist(df, source='social', target='source_url', create_using=nx.DiGraph()))

    for _, row in df.iterrows():
        G.add_node(row['source_url'], popularity=row['popularity'], timestamp=row['timestamp'], user_country=row['user_country'])

    pubs = []
    for r in G.predecessors(project_url+'#repository'):
        for n in G.predecessors(r):
            popularity = 0
            for path in nx.all_simple_paths(G, source=project_url+'#twitter', target=n):
                popularity += G.node[path[1]]['popularity']
            pubs.append([n , popularity])

    pubs = pd.DataFrame(pubs)
    pubs = pubs.sort_values(1, ascending=False)
    pubs[0].to_csv(filename, index=False)