# %%
# reacreating sbml model from query
import rdflib
import pickle, zlib, base64
from xmldiff import main
from lxml import etree
from cobra.io import read_sbml_model
from argparse import ArgumentParser
import requests
from urllib.parse import quote_plus


# %%
# RIMBO = rdflib.Namespace('http://rimbo.project-genesis.io#')
base_url = "http://localhost:3030/rev?query="
PREFIXES = """
PREFIX rimbo: <http://www.semanticweb.org/filipkro/ontologies/2023/4/rimbo#>
PREFIX comodi: <http://purl.uni-rostock.de/comodi/comodi#>
PREFIX BFO: <http://purl.obolibrary.org/obo/BFO_>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""
query = """SELECT ?patch ?file
    WHERE {
    ?rev a rimbo:Revision;
        rimbo:hasPatch ?p .
    ?p rimbo:binaryRepresentation ?patch;
        rimbo:patchTo / rimbo:binaryRepresentation ?file .
    } LIMIT 1"""

model_namespaces = {'rdf':"http://www.w3.org/1999/02/22-rdf-syntax-ns#", 'bqbiol':"http://biomodels.net/biology-qualifiers/", 'fbc':"http://www.sbml.org/sbml/level3/version1/fbc/version2", 'sbml':"http://www.sbml.org/sbml/level3/version1/core", 'html':"http://www.w3.org/1999/xhtml",'xsi':'http://www.w3.org/2001/XMLSchema-instance','dcterms':"http://purl.org/dc/terms/", 'vCard':"http://www.w3.org/2001/vcard-rdf/3.0#", 'vCard4':"http://www.w3.org/2006/vcard/ns#",'bqmodel':"http://biomodels.net/model-qualifiers/",'groups':"http://www.sbml.org/sbml/level3/version1/groups/version1"}

def restore_and_check_model(diff, base_tree):
    restored_tree = main.patch_tree(diff, base_tree, namespaces=model_namespaces)

    with open('tmp/model-from-query.xml', 'w') as fo:
        fo.write(etree.tostring(restored_tree, encoding='UTF-8',
                                xml_declaration=True,
                                pretty_print=True).decode())

    mod = read_sbml_model('tmp/model-from-query.xml')
    print(mod)

def get_model_from_fuseki():
    
    res = requests.get(base_url + quote_plus(PREFIXES + query))
    print(res.json())
    r = res.json()['results']['bindings'][0]
    diff = pickle.loads(zlib.decompress(base64.b64decode(r['patch']['value'])))
    base_tree = etree.fromstring(zlib.decompress(base64.b64decode(r['file']['value'])))

    restore_and_check_model(diff, base_tree)


def get_model_from_graph(graph):
    g = rdflib.Graph()
    g.parse(graph)
    res = g.query(query)
    for r in res:
        print(r)

    diff = pickle.loads(zlib.decompress(r[0].toPython()))
    base_tree = etree.fromstring(zlib.decompress(r[1].toPython()))

    restore_and_check_model(diff, base_tree)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--graph', default='')
    args = parser.parse_args()
    if args.graph == '':
        get_model_from_fuseki()
    else:
        get_model_from_graph(args.graph)