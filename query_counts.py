# Query a server at http://localhost:3030/rev
# for number of revisions of different type
# %%
import requests
from urllib.parse import quote_plus

base_url = "http://localhost:3030/rev?query="
PREFIXES = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rimbo: <http://rimbo.project-genesis.io#>
PREFIX comodi: <http://purl.uni-rostock.de/comodi/comodi#>
PREFIX BFO: <http://purl.obolibrary.org/obo/BFO_>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""

# PREFIX rimbo: <http://www.semanticweb.org/filipkro/ontologies/2023/4/rimbo#>
# %%
count_query = """
SELECT (COUNT(?rev) AS ?rev_count) 
WHERE {
    ?rev a rimbo:Revision .
} GROUP BY ?rev_count"""
print('total number of revisions')
query = base_url + quote_plus(PREFIXES + count_query)
r = requests.get(query)
print(r.json())

# %%
count_query = sparql = """
SELECT (COUNT(?change) AS ?rev_count)
WHERE {
    ?rev a rimbo:Revision;
        rimbo:hasChange / BFO:0000051 ?change .
    ?change a comodi:Update;
        comodi:affects ?gpa.
    ?gpa a rimbo:GeneProductAssociation .
} GROUP BY ?rev_count"""
print('number of gene-reaction rule revisions')
query = base_url + quote_plus(PREFIXES + count_query)
r = requests.get(query)
print(r.json())

# %%
count_query = sparql = """
SELECT (COUNT(?change) AS ?rev_count)
WHERE {
    ?rev a rimbo:Revision;
        rimbo:hasChange / BFO:0000051 ?change .
    ?change a comodi:Deletion .
} GROUP BY ?rev_count"""
print('numer of reaction deletion revisions')
query = base_url + quote_plus(PREFIXES + count_query)
r = requests.get(query)
print(r.json())

# %%
count_query = sparql = """
SELECT (COUNT(?change) AS ?rev_count)
WHERE {
    ?rev a rimbo:Revision;
        rimbo:hasChange / BFO:0000051 ?change .
    ?change a comodi:Update;
        comodi:affects ?bound .
    { ?bound a rimbo:UpperFluxBound }
    UNION
    { ?bound a rimbo:LowerFluxBound }
} GROUP BY ?rev_count"""
print('number of flux bound revisions')
query = base_url + quote_plus(PREFIXES + count_query)
r = requests.get(query)
print(r.json())