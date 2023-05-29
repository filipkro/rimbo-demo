import rdflib
from rdflib import Graph, Literal, BNode
from rdflib.namespace import RDF, PROV
import xmldiff
import numpy as np
import cobra
from cobra.io import read_sbml_model, write_sbml_model
import uuid
import base64, pickle, zlib
import random
from kb_utils import init_graph, init_examples, add_revision
import sys

RIMBO = rdflib.Namespace('http://www.semanticweb.org/filipkro/ontologies/2023/4/rimbo#')
REPRODUCEME = rdflib.Namespace('https://w3id.org/reproduceme#')
OBO = rdflib.Namespace('http://purl.obolibrary.org/obo/')
GO = rdflib.Namespace('http://purl.obolibrary.org/obo/GO_')
BFO = rdflib.Namespace('http://purl.obolibrary.org/obo/BFO_')
APO = rdflib.Namespace('http://purl.obolibrary.org/obo/APO_')
COMODI = rdflib.Namespace('http://purl.uni-rostock.de/comodi/comodi#')
EDAM = rdflib.Namespace('http://edamontology.org/format_')
MAMO = rdflib.Namespace('http://identifiers.org/mamo/MAMO_')
SBO = rdflib.Namespace('http://biomodels.net/SBO/SBO_')
CHEBI = rdflib.Namespace('http://purl.obolibrary.org/obo/CHEBI_')
NCIT = rdflib.Namespace('http://purl.obolibrary.org/obo/NCIT_')

RESTART = False

# setup rdflib w jena??
g = rdflib.Graph()
dummy_agent = RIMBO[f"sw-{uuid.uuid3(uuid.NAMESPACE_URL, 'dummy')}"]
if RESTART:
    init_graph(g)
    prev_model, patch_file = init_examples(g)
    g.add((dummy_agent, RDF.type, PROV.SoftwareAgent))
    g.add((dummy_agent, RIMBO.name, rdflib.Literal('dummy-agent')))
    model = read_sbml_model('data/y842r1.xml')
    oldfile = 'data/y842.xml'
else:
    g.parse('sim-output/revs-itr-500.ttl')
    prev_model = RIMBO['rev-964aeda3-8912-3477-8658-289b3b8ded28']
    patch_file = RIMBO['file-y8v842']
    model = read_sbml_model('data/y842r500.xml')
    oldfile = 'data/y842r500.xml'

ACTIONS = ['r', 'g', 'f']
PROBS = [0, 0.4, 0.6]
GPR_action = ['a', 'd']
GPR_probs = [0.7, 0.4]

NBR_REVISIONS = 20001
START_REV = 501


# prev_model = rdflib.BNode()
# patch_file = rdflib.BNode()

nbr_r = 0
nbr_g = 0
nbr_f = 0

print(f'size of g: {len(g)}')
print(f'prev: {prev_model}')
print(f'patch file: {patch_file}')

for i in range(START_REV, NBR_REVISIONS):
    print(f'iter {i}', end='\r')
    if i == 6000:
        PROBS = [0.001, 0.4, 0.599]

    action = random.choices(ACTIONS, PROBS)[0]
    ri = random.randrange(len(model.reactions))
    r = model.reactions[ri]
    rid = r.id
    annot = r.annotation
    sbo = annot['sbo'][0].split(':')[-1]
    kegg = annot['kegg.reaction'] if 'kegg.reaction' in annot else ''
    gene = random.choice(model.genes).id
    bound = ''
    val = 0.0
    if action == 'r':
        del model.reactions[ri]
        nbr_r += 1
    elif action == 'g':
        nbr_g += 1
        gpr = r.gene_reaction_rule
        if len(gpr) == 0:
            model.reactions[ri].gene_reaction_rule = gene
        elif not len(gpr.split('or')) < 3:
            model.reactions[ri].gene_reaction_rule = r.gene_reaction_rule + \
                f' or ({gene})'
        elif random.random() < 0.6:
            model.reactions[ri].gene_reaction_rule = r.gene_reaction_rule + \
                f' or ({gene})'
        else:
            disj = gpr.split(' or ')
            q = random.randrange(len(disj))
            if ' and ' in disj[q]:
                conj = disj[q].replace(')', '').replace('(', '').split(' and ')
                qq = random.randrange(len(conj))
                gene = conj[qq]
                del conj[qq]
                disj[q] = '(' + ' and '.join(conj) + ')'
            else:
                gene = disj[q]
                del disj[q]
            model.reactions[ri].gene_reaction_rule = ' or '.join(disj)
    elif action == 'f':
        nbr_f += 1
        if random.random() < 0.5:
            # lower bound
            val = float(random.randrange(-1000, int(r.upper_bound)))
            model.reactions[ri].lower_bound = val
            bound = 'LowerFluxBound'
        else:
            # upper bound
            val = float(random.randrange(int(r.lower_bound), 1000))
            model.reactions[ri].upper_bound = val
            bound = 'UpperFluxBound'

    # print(action)
    # print(val)
    write_sbml_model(model, 'tmp/rev.xml')
    prev_model, patch_file, oldfile = add_revision(g, str(i), action, prev_model, patch_file,
                              'tmp/rev.xml', oldfile, dummy_agent,
                              rid=rid, sbo=sbo, kegg=kegg, gene=gene,
                              bound=bound, value=val)
    
    if i % 500 == 0:
        print()
        print(f'added {i+1} revisions to graph (itr {i})')
        print(f'size of graph: {len(g)}')
        g.serialize(f'sim-output/revs-itr-{i}.ttl')
        with open(f'sim-output/prev_model-{i}.txt', 'w') as fo:
            fo.write(f'added {i} revisions to graph (itr {i})\n')
            fo.write(f'size of graph: {len(g)}\n')
            fo.write(f'number of removed reactions: {nbr_r}\n')
            fo.write(f'number of modified gene-reaction-rules: {nbr_g}\n')
            fo.write(f'number of modified flux bounds: {nbr_f}\n')
            fo.write('\n')
            fo.write('previous model:\n')
            fo.write(str(prev_model))
            fo.write('\n\n')
            fo.write('patch_to:\n')
            fo.write(str(patch_file))

    
g.serialize('done.ttl')
print(prev_model)