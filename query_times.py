# query a server at http://localhost:3030/rev
# 100 times and measure the query time

import requests
from urllib.parse import quote_plus
import time, pickle
from functools import wraps
import numpy as np
from argparse import ArgumentParser

base_url = "http://localhost:3030/rev?query="
PREFIXES = """
PREFIX rimbo: <http://rimbo.project-genesis.io#>
PREFIX comodi: <http://purl.uni-rostock.de/comodi/comodi#>
PREFIX BFO: <http://purl.obolibrary.org/obo/BFO_>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""
# PREFIX rimbo: <http://www.semanticweb.org/filipkro/ontologies/2023/4/rimbo#>

def timeit_once(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        return result, end - start
    return wrapper

@timeit_once
def run_query(g, r):
    sparql = f"""
SELECT ?patch ?file 
WHERE {{
    ?rev a rimbo:Revision;
        rimbo:hasPatch ?p ;
        rimbo:hasChange / BFO:0000051 ?change .
    ?change a comodi:Update;
        rimbo:id ?reaction;
        comodi:affects ?gpa .
    FILTER (?reaction="{r}"^^xsd:string)
    ?gpa a rimbo:GeneProductAssociation;
        rimbo:name ?gene .
    FILTER (?gene="{g}"^^xsd:string)
    ?p rimbo:binaryRepresentation ?patch;
        rimbo:patchTo / rimbo:binaryRepresentation ?file .
}}"""
    r = requests.get(base_url + quote_plus(PREFIXES + sparql))

def run_exp(args):
    times = []
    with open('query-exp/pairs.pkl', 'rb') as fi:
        # gene-reaction pairs available in all databases
        pairs = pickle.load(fi)
        
    for i in range(5):
        # initialize server
        (g, r) = pairs[-i]
        _, t = run_query(g, r)

    for i in range(100):
        (g, r) = pairs[i]
        _, t = run_query(g, r)
        times.append(t)

    print(times)
    with open(f'query-exp/time-{args.db}.pkl', 'wb') as fo:
        pickle.dump(times, fo)
    print(np.mean(times))

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('db')
    args = parser.parse_args()
    run_exp(args)