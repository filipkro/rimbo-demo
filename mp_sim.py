import multiprocessing as mp
import uuid
from cobra.io import read_sbml_model, write_sbml_model
import zlib, base64, shutil, pickle
from xmldiff import main
import random
import rdflib
from rdflib.namespace import RDF, PROV, XSD


RIMBO = rdflib.Namespace('https://project-genesis.io/rimbo#')
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

START = 0
class MpGen:
    def __init__(self):
        self.dummy_agent = RIMBO[f"sw-{uuid.uuid3(uuid.NAMESPACE_URL, 'dummy')}"]
        self.ACTIONS = ['r', 'g', 'f']
        self.PROBS = [0.2, 0.8, 0]
        self.GPR_action = ['a', 'd']
        self.GPR_probs = [0.7, 0.4]

        self.NBR_CYC = 20

    def init_rev(self, model, rev_to, agent):
        trip = []
        trip.append((model, RDF.type, RIMBO.Revision))
        trip.append((model, RDF.type, MAMO['0000009']))
        trip.append((model, RIMBO.revisionTo, rev_to))
        trip.append((model, RIMBO.createdBy, agent))

        proc = rdflib.BNode()
        trip.append((proc, RDF.type, GO['0008152']))
        trip.append((model, MAMO.isUsedToModel, proc))

        return trip
    
    def rev_reaction(self, change, rid, sbo, kegg, action='Deletion'):
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
    
    def rev_gpa(self, change, rid, gene):
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
    
    def rev_flux(self, change, rid, bound, value):
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

    def ar(self, i, action, rev_to, patch_to, newfile, oldfile, agent, branch,
           rid='', sbo='', kegg='', gene='', bound=0.0, value=''):
        trip = []
        m_id = f"branch-{branch}-" + \
            f"{str(uuid.uuid3(uuid.NAMESPACE_URL, 'y8v842r' + i + branch))}"
        model = RIMBO[f"rev-{m_id}"]
        trp = self.init_rev(model, rev_to, agent)
        trip.extend(trp)

        ch = RIMBO[f"change-{m_id}"]
        trip.append((ch, RDF.type, COMODI.Change))
        trip.append((model, RIMBO.hasChange, ch))

        if action == 'r':
            trip.extend(self.rev_reaction(ch, rid, sbo, kegg))
        elif action == 'g':
            trip.extend(self.rev_gpa(ch, rid, gene))
        elif action == 'f':
            trip.extend(self.rev_flux(ch, rid, bound, value))

        if int(i) % 50 == 0 or int(i) % 9001 == 0:

            patch_to = RIMBO[f'file-y8v842r{i + branch}']
            trip.append((patch_to, RDF.type, EDAM['2585']))
            with open(newfile, 'rb') as fi:
                zz = base64.b64encode(zlib.compress(fi.read(),
                                                    zlib.Z_BEST_COMPRESSION))
            trip.append((patch_to, RIMBO.binaryRepresentation,
                rdflib.Literal(zz, datatype=XSD.base64Binary)))
            trip.append((model, RIMBO.isImplementedAs, patch_to))

            oldfile = f'data-par/y842r{i + branch}.xml'
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

            # print()
            # print(oldfile)
            # print(newfile)
            # print('getting diff...')
            diff = main.diff_files(oldfile, newfile,
                                           diff_options={'fast_match':True})
            # print()
            # print(action, len(diff))
            # print('diff found')
            zz = base64.b64encode(zlib.compress(pickle.dumps(diff)))
            trip.append((patch, RIMBO.binaryRepresentation,
                rdflib.Literal(zz, datatype=XSD.base64Binary)))
        
        return trip, model, patch_to, oldfile

    # trp, prev_model, patch_file, oldfile

    def gen_triples(self, prev_model, patch_file, oldfile, branch, start_i):
        trip = []
        model = read_sbml_model(oldfile)

        # for i in range(start_i, start_i + 100):
        for i in range(0, 50):
            if branch == 'a':
                action = random.choices(self.ACTIONS, self.PROBS)[0]
            elif branch in ['b', 'c']:
                action = random.choices(self.ACTIONS, [0.5, 0.5, 0])[0]
            else:
                action = random.choices(self.ACTIONS, [0.7, 0.3, 0])[0]
            ri = random.randrange(len(model.reactions))
            r = model.reactions[ri]
            rid = r.id
            annot = r.annotation
            sbo = annot['sbo'].split(':')[-1]
            kegg = annot['kegg.reaction'] if 'kegg.reaction' in annot else ''
            gene = random.choice(model.genes).id
            bound = ''
            val = 0.0
            nbr_r = 0
            nbr_g = 0
            nbr_f = 0

            # print(sbo)
            # print(annot['sbo'])
            if action == 'r':
                model.reactions[ri].remove_from_model()
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
                if abs(r.lower_bound - r.upper_bound) <= 100:
                    model.reactions[ri].upper_bound = 1000.0
                    model.reactions[ri].lower_bound = 0.0
                    bound = 'UpperFluxBound'
                    val = 1000.0
                elif random.random() < 0.5:
                    # lower bound
                    val = float(random.randrange(-1000, int(r.upper_bound),
                                                 step=50))

                    model.reactions[ri].lower_bound = val \
                        if val <= r.upper_bound else -1000.0
                    bound = 'LowerFluxBound'
                else:
                    # upper bound
                    val = float(random.randrange(int(r.lower_bound), 1000,
                                                 step=50))
                    model.reactions[ri].upper_bound = val \
                        if val >= r.lower_bound else 1000.0
                    bound = 'UpperFluxBound'
            
            fname = f'tmp-par/rev-{branch}.xml'
            write_sbml_model(model, fname)
            trp, prev_model, patch_file, oldfile = self.ar(str(i+START+100*(start_i-START)),
                                                           action, prev_model,
                                                           patch_file, fname,
                                                           oldfile,
                                                           self.dummy_agent,
                                                           branch, rid=rid,
                                                           sbo=sbo, kegg=kegg,
                                                           gene=gene, value=val,
                                                           bound=bound)
            trip.extend(trp)
        return trip, prev_model, patch_file, oldfile, nbr_f, nbr_g, nbr_r#, i #, nbrs
    
    def mp_gen(self, start_i):

        prev_model = RIMBO[f"rev-{str(uuid.uuid3(uuid.NAMESPACE_URL, 'y8v842r' + str(start_i-1)))}"]
        patch_file = RIMBO[f'file-y8v842r{start_i-1}']
        oldfile = f'data-par/y842r{start_i-1}.xml'
        mod_a = RIMBO[f"rev-branch-a-{str(uuid.uuid3(uuid.NAMESPACE_URL, 'y8v842r9450a'))}"]
        mod_b = RIMBO[f"rev-branch-b-{str(uuid.uuid3(uuid.NAMESPACE_URL, 'y8v842r9450b'))}"]
        mod_c = RIMBO[f"rev-branch-c-{str(uuid.uuid3(uuid.NAMESPACE_URL, 'y8v842r9450c'))}"]
        mod_d = RIMBO[f"rev-branch-d-{str(uuid.uuid3(uuid.NAMESPACE_URL, 'y8v842r9450d'))}"]
        # mod_a = RIMBO['rev-branch-a-2a98dec5-5dfd-33f6-ade1-9643f2a70fc9']
        # mod_b = RIMBO['rev-branch-b-8abb1391-ec49-367e-82e8-b27001ee4085']
        # mod_c = RIMBO['rev-branch-c-e0b7101d-959a-3ef0-9494-a96a5fd81a8e']
        # mod_d = RIMBO['rev-branch-d-0c52a37e-417e-31c4-a699-1b0bb24aebe3']

        patch_a = RIMBO[f'file-y8v842r9450a']
        patch_b = RIMBO[f'file-y8v842r9450b']
        patch_c = RIMBO[f'file-y8v842r9450c']
        patch_d = RIMBO[f'file-y8v842r9450d']

        fa = 'data-par/y842r9450a.xml'
        fb = 'data-par/y842r9450b.xml'
        fc = 'data-par/y842r9450c.xml'
        fd = 'data-par/y842r9450a.xml'

        nbr_r = 0
        nbr_g = 0
        nbr_f = 0

        # self.NBR_CYC = 2
        # gen_triples(self, prev_model, patch_file, oldfile, branch, nbrs, start_i)
        # return trip, prev_model, patch_file, oldfile#, i #, nbrs
        g = rdflib.Graph()
        g.parse('data-par/revs-par-itr-58.ttl')
        for i in range(0, self.NBR_CYC):
            print(len(g))
            print(f"outer itr {i}")
            # if i == 10:
            #     print('changing action probs')
            #     self.PROBS = [0.001, 0.9, 0.099]
            with mp.Pool(processes=4) as pool:
                jobs = [[mod_a, patch_a, fa, 'a', start_i + i],
                        [mod_b, patch_b, fb, 'b', start_i + i],
                        [mod_c, patch_c, fc, 'c', start_i + i],
                        [mod_d, patch_d, fd, 'd', start_i + i]]
                
                res = pool.starmap(self.gen_triples, jobs)
                mod_a = res[0][1]
                mod_b = res[1][1]
                mod_c = res[2][1]
                mod_d = res[3][1]

                patch_a = res[0][2]
                patch_b = res[1][2]
                patch_c = res[2][2]
                patch_d = res[3][2]

                fa = res[0][3]
                fb = res[1][3]
                fc = res[2][3]
                fd = res[3][3]
                for p in res:
                    nbr_f += p[4]
                    nbr_g += p[5]
                    nbr_r += p[6]
                    for t in p[0]:
                        g.add(t)

            g.serialize(f'data-par/revs-par-itr-{59+i}.ttl')
            with open(f'data-par/info-itr-{i}.txt', 'w') as fo:
                fo.write(f'nbr f: {nbr_f}\n')
                fo.write(f'nbr g: {nbr_g}\n')
                fo.write(f'nbr r: {nbr_r}\n')
                fo.write(f'size of graph: {len(g)}')
            size_query = """
SELECT (COUNT(?rev) AS ?rev_count) 
WHERE {
    ?rev a rimbo:Revision .
} GROUP BY ?rev_count"""
            gsize = g.query(size_query)
            for a in gsize:
                pass
            nbr_rev = a[0].toPython()
            print(nbr_rev)
            if nbr_rev >= 31400:
                break
            # break

    #  return trip, prev_model, patch_file, oldfile, nbr_f, nbr_g, nbr_r
    
    def gen_ex(self, a, b):
        return [(a,'lol',b), (a, 'lol2',b)]

    def run_mp(self):
        print('starting')
        with mp.Pool(processes=2) as pool:
            print('in with')
            # jobs = [[0,'a'],[1,'b'],[2,'c']]
            jobs = [(0,'a'),(1,'b'),(2,'c')]
            results = pool.starmap(self.gen_ex, jobs)

            return results


if __name__ == '__main__':
    print()
    mpg = MpGen()
    # res = mpg.run_mp()
    print('running')
    mpg.mp_gen(START)
    print('done??')
    # for a in res:
    #     print(a)
    # print(res)