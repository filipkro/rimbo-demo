# iteratively revisions to models, four parallel chains

import multiprocessing as mp
import uuid
from cobra.io import read_sbml_model, write_sbml_model
import random
import rdflib
from rdflib.namespace import PROV, RDF
from argparse import ArgumentParser

from graph_utils import init_graph, init_examples, revision_triples

# RIMBO = rdflib.Namespace('http://www.semanticweb.org/
# filipkro/ontologies/2023/4/rimbo#')
RIMBO = rdflib.Namespace('http://rimbo.project-genesis.io#')

class MpGen:
    def __init__(self, args=None):
        self.dummy_agent = RIMBO[f"sw-{uuid.uuid3(uuid.NAMESPACE_URL, 'dummy')}"]
        self.ACTIONS = ['r', 'g', 'f']
        self.PROBS = [0.2, 0.7, 0.1]
        self.NBR_CYC = args.nbr_cyc
        self.args = args

    def gen_triples(self, prev_model, patch_file, oldfile, branch, start_i):
        # generate random revision to model
        trip = []
        model = read_sbml_model(oldfile)

        for i in range(0, 100):
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
            
            if action == 'r':
                model.reactions[ri].remove_from_model()
            elif action == 'g':
                gpr = r.gene_reaction_rule
                if len(gpr) == 0:
                    model.reactions[ri].gene_reaction_rule = gene
                elif not len(gpr.split('or')) < 3:
                    model.reactions[ri].gene_reaction_rule = \
                        r.gene_reaction_rule + f' or ({gene})'
                elif random.random() < 0.6:
                    model.reactions[ri].gene_reaction_rule = \
                        r.gene_reaction_rule + f' or ({gene})'
                else:
                    disj = gpr.split(' or ')
                    q = random.randrange(len(disj))
                    if ' and ' in disj[q]:
                        conj = disj[q].replace(')', '').replace('(', 
                                                            '').split(' and ')
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

            trp, prev_model, patch_file, oldfile = \
                revision_triples(str(i+self.start_i+100*(start_i-self.start_i)),
                                 action, prev_model, patch_file, fname, oldfile,
                                 self.dummy_agent, branch, rid=rid, sbo=sbo,
                                 kegg=kegg, gene=gene, value=val, bound=bound)
            trip.extend(trp)
        return trip, prev_model, patch_file, oldfile
    
    def mp_gen(self):
        # run outer loop with four parallel revision chains,
        # serialize graph every iteration
        if self.args.previous_model != '':
            fa = f'data-par/{self.args.previous_model}a.xml'
            fb = f'data-par/{self.args.previous_model}b.xml'
            fc = f'data-par/{self.args.previous_model}c.xml'
            fd = f'data-par/{self.args.previous_model}d.xml'

            m_id = f'y8v{self.args.previous_model[1:]}'

            mod_a = RIMBO[f"rev-branch-a-{str(uuid.uuid3(uuid.NAMESPACE_URL,
                                                         f'{m_id}a'))}"]
            mod_b = RIMBO[f"rev-branch-b-{str(uuid.uuid3(uuid.NAMESPACE_URL,
                                                         f'{m_id}b'))}"]
            mod_c = RIMBO[f"rev-branch-c-{str(uuid.uuid3(uuid.NAMESPACE_URL,
                                                         f'{m_id}c'))}"]
            mod_d = RIMBO[f"rev-branch-d-{str(uuid.uuid3(uuid.NAMESPACE_URL,
                                                         f'{m_id}d'))}"]

            patch_a = RIMBO[f'file-{m_id}a']
            patch_b = RIMBO[f'file-{m_id}b']
            patch_c = RIMBO[f'file-{m_id}c']
            patch_d = RIMBO[f'file-{m_id}d']

        g = rdflib.Graph()
        if self.args.init_graph == 1:
            init_graph(g)
            g.add((self.dummy_agent, RDF.type, PROV.SoftwareAgent))
            g.add((self.dummy_agent, RIMBO.name, rdflib.Literal('dummy-agent')))
        if self.args.init_examples == 1:
            mod_a, patch_a, fa  = init_examples(g)
            mod_b = mod_c = mod_d = mod_a
            patch_b = patch_c = patch_d = patch_a
            fb = fc = fd = fa

        if self.args.graph_itr != -1:
            g.parse(f'data-par/revs-par-itr-{self.args.graph_itr}.ttl')

        self.start_i = int(patch_a.toPython().split('file-')[-1].split('r')[-1][:-1])
        for i in range(self.NBR_CYC):
            print(len(g))
            print(f"outer itr {i}")
            with mp.Pool(processes=4) as pool:
                jobs = [[mod_a, patch_a, fa, 'a', self.start_i + i],
                        [mod_b, patch_b, fb, 'b', self.start_i + i],
                        [mod_c, patch_c, fc, 'c', self.start_i + i],
                        [mod_d, patch_d, fd, 'd', self.start_i + i]]
                
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
                    for t in p[0]:
                        g.add(t)

            g.serialize(f'tmp/revs-par-itr-{i}.ttl')
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


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--init_graph', default=0, type=int)
    parser.add_argument('--init_examples', default=0, type=int)
    parser.add_argument('--previous_model', default='')
    parser.add_argument('--graph_itr', default=-1, type=int)
    parser.add_argument('--nbr_cyc', default=20, type=int)
    args = parser.parse_args()
    
    assert any([args.init_graph, args.graph_itr != -1])
    assert any([args.init_examples, args.previous_model != ''])

    mpg = MpGen(args)
    print('running')
    mpg.mp_gen()
    print('done??')