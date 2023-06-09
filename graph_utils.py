# util functions to add revisions of models to graph

import rdflib
from rdflib.namespace import PROV, RDF, XSD
import uuid
import pandas as pd
from xmldiff import main
import base64, pickle, zlib, shutil

# RIMBO = rdflib.Namespace('http://www.semanticweb.org/
# filipkro/ontologies/2023/4/rimbo#')
RIMBO = rdflib.Namespace('http://rimbo.project-genesis.io#')
REPRODUCEME = rdflib.Namespace('https://w3id.org/reproduceme#')
GO = rdflib.Namespace('http://purl.obolibrary.org/obo/GO_')
BFO = rdflib.Namespace('http://purl.obolibrary.org/obo/BFO_')
APO = rdflib.Namespace('http://purl.obolibrary.org/obo/APO_')
COMODI = rdflib.Namespace('http://purl.uni-rostock.de/comodi/comodi#')
EDAM = rdflib.Namespace('http://edamontology.org/format_')
MAMO = rdflib.Namespace('http://identifiers.org/mamo/MAMO_')
SBO = rdflib.Namespace('http://biomodels.net/SBO/SBO_')
CHEBI = rdflib.Namespace('http://purl.obolibrary.org/obo/CHEBI_')
NCIT = rdflib.Namespace('http://purl.obolibrary.org/obo/NCIT_')

def init_graph(g):
    # initialise namespaces in graph
    g.bind('rimbo', RIMBO)
    g.bind('prov', PROV)
    g.bind('reproduceme', REPRODUCEME)
    g.bind('GO', GO)
    g.bind('BFO', BFO)
    g.bind('APO', APO)
    g.bind('comodi', COMODI)
    g.bind('edam', EDAM)
    g.bind('mamo', MAMO)
    g.bind('SBO', SBO)
    g.bind('CHEBI', CHEBI)
    g.bind('NCIT', NCIT)

def init_rev_triples(model, rev_to, agent):
    # generate list of triples needed to initialise revision in graph
    trip = []
    trip.append((model, RDF.type, RIMBO.Revision))
    trip.append((model, RDF.type, MAMO['0000009']))
    trip.append((model, RIMBO.revisionTo, rev_to))
    trip.append((model, RIMBO.createdBy, agent))

    proc = rdflib.BNode()
    trip.append((proc, RDF.type, GO['0008152']))
    trip.append((model, MAMO.isUsedToModel, proc))

    return trip

def init_rev(g, model, rev_to, agent):
    # add triples in list to graph
    triples = init_rev_triples(model, rev_to, agent)
    for t in triples:
        g.add(t)

def add_revision(g, i, action, rev_to, patch_to, newfile, oldfile, agent, branch='',
                 rid='', sbo='', kegg='', gene='', bound=0.0, value=''):
    # add triples to graph
    triples, model, patch_to, oldfile = revision_triples(i, action, rev_to,
                                                         patch_to, newfile,
                                                         oldfile, agent, branch,
                                                         rid, sbo, kegg, gene,
                                                         bound, value)
    
    for t in triples:
        g.add(t)
    
    return model, patch_to, oldfile

def revision_triples(i, action, rev_to, patch_to, newfile, oldfile, agent,
                     branch='', rid='', sbo='', kegg='', gene='', bound=0.0,
                     value=''):
    # generate triples describing a specified revision
    trip = []

    m_id = f"branch-{branch}-" + \
        f"{str(uuid.uuid3(uuid.NAMESPACE_URL, 'y8v842r' + i + branch))}" \
            if branch != '' else str(uuid.uuid3(uuid.NAMESPACE_URL,
                                                'y8v842r' + i))
        
    model = RIMBO[f"rev-{m_id}"]
    trp = init_rev_triples(model, rev_to, agent)
    trip.extend(trp)

    ch = RIMBO[f"change-{m_id}"]
    trip.append((ch, RDF.type, COMODI.Change))
    trip.append((model, RIMBO.hasChange, ch))

    if action == 'r':
        trip.extend(rev_reaction_triples(ch, rid, sbo, kegg))
    elif action == 'g':
        trip.extend(rev_gpa_triples(ch, rid, gene))
    elif action == 'f':
        trip.extend(rev_flux_triples(ch, rid, bound, value))

    if int(i) % 100 == 0:

        patch_to = RIMBO[f'file-y8v842r{i + branch}']
        trip.append((patch_to, RDF.type, EDAM['2585']))
        with open(newfile, 'rb') as fi:
            zz = base64.b64encode(zlib.compress(fi.read(),
                                                zlib.Z_BEST_COMPRESSION))
        trip.append((patch_to, RIMBO.binaryRepresentation,
            rdflib.Literal(zz, datatype=XSD.base64Binary)))
        trip.append((model, RIMBO.isImplementedAs, patch_to))

        # oldfile = f'data-par/y842r{i + branch}.xml'
        oldfile = f'tmp/y842r{i + branch}.xml'
        shutil.copyfile(newfile, oldfile)
    else:
        patch = RIMBO[f"patch-{m_id}"]
        trip.append((patch, RDF.type, RIMBO.DiffPatch))
        trip.append((model, RIMBO.hasPatch, patch))
        sw = rdflib.BNode()
        trip.append((sw, RDF.type, REPRODUCEME.Software))
        trip.append((sw, RIMBO.name, rdflib.Literal('xmldiff')))
        trip.append((sw, RIMBO.version, rdflib.Literal('2.5.0')))
        trip.append((patch, RIMBO.usesSoftware, sw))
        trip.append((patch, RIMBO.patchTo, patch_to))

        diff = main.diff_files(oldfile, newfile,
                                        diff_options={'fast_match':True})

        zz = base64.b64encode(zlib.compress(pickle.dumps(diff)))
        trip.append((patch, RIMBO.binaryRepresentation,
            rdflib.Literal(zz, datatype=XSD.base64Binary)))
    
    return trip, model, patch_to, oldfile

def rev_reaction(g, change, rid, sbo, kegg, action='Deletion'):
    # add triples to graph
    triples = rev_reaction_triples(change, rid, sbo, kegg, action)
    for t in triples:
        g.add(t)

def rev_reaction_triples(change, rid, sbo, kegg, action='Deletion'):
        # generate triples for deleted reaction revision
        trip = []
        ch = rdflib.BNode()
        trip.append((ch, RDF.type, COMODI[action]))
        trip.append((ch, RIMBO.id, rdflib.Literal(rid, datatype=XSD.string)))
        trip.append((change, BFO['0000051'], ch))
        r = rdflib.BNode()
        trip.append((r, RDF.type, SBO[sbo]))
        trip.append((ch, COMODI.affects, r))
        if kegg != '':
            kpath = 'https://www.genome.jp/entry/' + kegg
            trip.append((r, RDF.type, SBO['0000554']))
            trip.append((r, RIMBO.xref, rdflib.Literal(kpath,
                                                       datatype=XSD.anyURI)))
            
        return trip

def rev_gpa(g, change, rid, gene):
    # add  triples to graph
    triples = rev_gpa_triples(change, rid, gene)
    for t in triples:
        g.add(t)

def rev_gpa_triples(change, rid, gene):
        # generate triples for updated gpa for reaction
        trip = []
        ch = rdflib.BNode()
        trip.append((ch, RDF.type, COMODI.Update))
        trip.append((change, BFO['0000051'], ch))
        trip.append((ch, RIMBO.id, rdflib.Literal(rid, datatype=XSD.string)))
        gpa = rdflib.BNode()
        trip.append((gpa, RDF.type, RIMBO.GeneProductAssociation))
        trip.append((ch, COMODI.affects, gpa))
        trip.append((gpa, RIMBO.name,
                     rdflib.Literal(gene, datatype=XSD.string)))

        return trip

def rev_flux(g, change, rid, bound, value):
    # add triples to graph
    triples = rev_flux_triples(change, rid, bound, value)
    for t in triples:
        g.add(t)

def rev_flux_triples(change, rid, bound, value):
    # generate triples for updated flux bound
    trip = []
    ch = rdflib.BNode()
    trip.append((ch, RDF.type, COMODI.Update))
    trip.append((change, BFO['0000051'], ch))
    trip.append((ch, RIMBO.id, rdflib.Literal(rid, datatype=XSD.string)))
    bnode = rdflib.BNode()
    trip.append((bnode, RDF.type, RIMBO[bound]))
    trip.append((ch, COMODI.affects, bnode))
    trip.append((bnode, RIMBO.value, rdflib.Literal(value, datatype=XSD.float)))

    return trip

def init_examples(g):
    # initialise examples, base model, yeast8v8.4.1
    with open('data/y841.xml', 'rb') as fi:
        zz = base64.b64encode(zlib.compress(fi.read(),
                                            zlib.Z_BEST_COMPRESSION))
    m1 = RIMBO['model-y841']
    pub = rdflib.BNode()
    g.add((pub, RDF.type, RIMBO.Publication))
    g.add((pub, RIMBO.doi,
           rdflib.Literal('https://doi.org/10.1038/s41467-019-11581-3',
                          datatype=XSD.string)))
    sys_bio = RIMBO["org-"
                    f"{str(uuid.uuid3(uuid.NAMESPACE_URL, 'SysBioChalmers'))}"]
    g.add((sys_bio, RDF.type, PROV.Organization))
    g.add((sys_bio, RIMBO.name, rdflib.Literal('SysBioChalmers',
                                               datatype=XSD.string)))
    proc = rdflib.BNode()
    g.add((proc, RDF.type, GO['0008152']))
    m1_file = RIMBO['file-y841']
    g.add((m1_file, RDF.type, EDAM['2585']))
    g.add((m1_file, RIMBO.binaryRepresentation,
           rdflib.Literal(zz, datatype=XSD.base64Binary)))
    g.add((m1, RDF.type, MAMO['0000009']))
    g.add((m1, RIMBO.createdBy, sys_bio))
    g.add((m1, RIMBO.withPublication, pub))
    g.add((m1, MAMO.isUsedToModel, proc))
    g.add((m1, RIMBO.isImplementedAs, m1_file))

    # first revision, yeast8v8.4.2
    m42 = RIMBO[f"rev-{str(uuid.uuid3(uuid.NAMESPACE_URL, 'y8v842'))}"]
    init_rev(g, m42, m1, sys_bio)

    change = RIMBO[f"change-{str(uuid.uuid3(uuid.NAMESPACE_URL, 'y8v842'))}"]
    g.add((change, RDF.type, COMODI.Change))
    g.add((m42, RIMBO.hasChange, change))
    reacts = pd.read_csv('data/reacts.csv', delimiter=',', header=None)[[1,10]]
    for _, react in reacts.iterrows():
        sbo = [a for a in react[10].split(';') if 'sbo' in a][0].split(':')[-1]
        if 'kegg' in react[10]:
            kegg = [a for a in react[10].split(';')
                    if 'kegg' in a][0].split('/')[-1]
        else:
            kegg = ''
        rev_reaction(g, change, react[1], sbo, kegg, action='Insertion')
        
    reason = RIMBO[f"reason-{str(uuid.uuid3(uuid.NAMESPACE_URL, 'y8v842'))}"]
    g.add((reason, RDF.type, COMODI.KnowledgeGain))
    obs = rdflib.BNode()
    g.add((obs, RDF.type, APO['0000095']))
    g.add((reason, RIMBO.aboutObservable, obs))
    chem = rdflib.BNode()
    g.add((chem, RDF.type, CHEBI['35748']))
    g.add((obs, RIMBO.ofMaterialEntity, chem))
    g.add((m42, RIMBO.hasReason, reason))
    
    m2_file = RIMBO['file-y8v842']
    g.add((m2_file, RDF.type, EDAM['2585']))
    with open('data/y842.xml', 'rb') as fi:
        zz = base64.b64encode(zlib.compress(fi.read(),
                                            zlib.Z_BEST_COMPRESSION))
    g.add((m2_file, RIMBO.binaryRepresentation,
           rdflib.Literal(zz, datatype=XSD.base64Binary)))
    g.add((m42, RIMBO.isImplementedAs, m2_file))

    # second revision, abductive reasoning removing gene from GPA
    fol = RIMBO[f"sw-{uuid.uuid3(uuid.NAMESPACE_URL, 'fol')}"]
    g.add((fol, RDF.type, PROV.SoftwareAgent))
    g.add((fol, RIMBO.name, rdflib.Literal('fol-abd01')))

    rev = RIMBO[f"rev-{str(uuid.uuid3(uuid.NAMESPACE_URL, 'y8v842r1'))}"]
    init_rev(g, rev, m42, fol)

    change = RIMBO[f"change-{str(uuid.uuid3(uuid.NAMESPACE_URL, 'y8v842r1'))}"]
    g.add((change, RDF.type, COMODI.Change))
    rev_gpa(g, change, 'r_0250', 'YJL130C')
    g.add((rev, RIMBO.hasChange, change))

    reason = RIMBO[f"reason-{str(uuid.uuid3(uuid.NAMESPACE_URL, 'y8v842r1'))}"]
    g.add((reason, RDF.type, COMODI.MismatchWithPublication))
    g.add((rev, RIMBO.hasReason, reason))
    pub = rdflib.BNode()
    g.add((pub, RDF.type, REPRODUCEME.Publication))
    g.add((pub, RIMBO.doi,
           rdflib.Literal('https://doi.org/10.1038/nature00935')))
    g.add((reason, RIMBO.withPublication, pub))
    obs = rdflib.BNode()
    g.add((obs, RDF.type, APO['0000217']))
    g.add((reason, RIMBO.aboutObservable, obs))
    gene = rdflib.BNode()
    g.add((gene, RDF.type, NCIT['C16612']))
    g.add((gene, RDF.type, SBO['0000554']))
    g.add((gene, RIMBO.xref,
           rdflib.Literal('https://yeastgenome.org/locus/S000003666',
                          datatype=XSD.anyURI)))
    g.add((gene, RIMBO.name, rdflib.Literal('YJL130C', datatype=XSD.string)))
    g.add((obs, RIMBO.ofMaterialEntity, gene))

    patch = RIMBO[f"patch-{str(uuid.uuid3(uuid.NAMESPACE_URL, 'y8v842r1'))}"]
    g.add((patch, RDF.type, RIMBO.DiffPatch))
    g.add((rev, RIMBO.hasPatch, patch))
    sw = rdflib.BNode()
    g.add((sw, RDF.type, REPRODUCEME.Software))
    g.add((sw, RIMBO.name, rdflib.Literal('xmldiff')))
    g.add((sw, RIMBO.version, rdflib.Literal('2.5.0')))
    g.add((patch, RIMBO.usesSoftware, sw))
    g.add((patch, RIMBO.patchTo, m2_file))

    print('getting diff...')
    diff = main.diff_files('data/y842.xml', 'data/y842r1.xml',
                           diff_options={'fast_match':True})
    print('diff found')
    zz = base64.b64encode(zlib.compress(pickle.dumps(diff)))
    g.add((patch, RIMBO.binaryRepresentation,
           rdflib.Literal(zz, datatype=XSD.base64Binary)))

    return rev, m2_file, 'data/y842r1.xml'