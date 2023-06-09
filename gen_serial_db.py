import rdflib
from rdflib.namespace import RDF, PROV
from cobra.io import read_sbml_model, write_sbml_model
import uuid
import random
from argparse import ArgumentParser

from graph_utils import init_graph, init_examples, add_revision

# RIMBO = rdflib.Namespace('http://www.semanticweb.org/
# filipkro/ontologies/2023/4/rimbo#')
RIMBO = rdflib.Namespace('http://rimbo.project-genesis.io#')

def generate_graph(args):
    # generate iterative revisions
    g = rdflib.Graph()
    dummy_agent = RIMBO[f"sw-{uuid.uuid3(uuid.NAMESPACE_URL, 'dummy')}"]

    if args.previous_model != '':
        oldfile = f'{args.previous_model}'
        m_id = f"y8v{args.previous_model.split('/')[-1].split('.')[0][1:]}"
        prev_model = RIMBO[f"rev-{str(uuid.uuid3(uuid.NAMESPACE_URL, f'{m_id}'))}"]
        patch_file = RIMBO[f'file-{m_id}']

    if args.init_graph == 1:
        init_graph(g)
        g.add((dummy_agent, RDF.type, PROV.SoftwareAgent))
        g.add((dummy_agent, RIMBO.name, rdflib.Literal('dummy-agent')))

    if args.init_examples == 1:
        prev_model, patch_file, oldfile = init_examples(g)

    if args.graph_itr != -1:
        g.parse(f'sim-output/revs-itr-{args.graph_itr}.ttl')

    START_REV = int(patch_file.toPython().split('file-')[-1].split('r')[-1])
    model = read_sbml_model(oldfile)

    ACTIONS = ['r', 'g', 'f']
    PROBS = [0.2, 0.7, 0.1]

    NBR_REVISIONS = START_REV + args.nbr_cyc

    print(f'size of g: {len(g)}')
    print(f'prev: {prev_model}')
    print(f'patch file: {patch_file}')

    for i in range(START_REV, NBR_REVISIONS):
        print(f'iter {i}', end='\r')

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

        write_sbml_model(model, 'tmp/rev.xml')
        prev_model, patch_file, oldfile = add_revision(g, str(i), action,
                                                       prev_model, patch_file,
                                                       'tmp/rev.xml', oldfile,
                                                       dummy_agent, rid=rid,
                                                       sbo=sbo, kegg=kegg,
                                                       gene=gene, bound=bound,
                                                       value=val)
        
        if i % 500 == 0:
            print()
            print(f'added {i+1} revisions to graph (itr {i})')
            print(f'size of graph: {len(g)}')
            g.serialize(f'tmp/revs-itr-{i}.ttl')

        
    g.serialize('done.ttl')
    print(prev_model)


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
    generate_graph(args)
