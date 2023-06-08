# create box plots of query times for demonstration

import pickle
import matplotlib.pyplot as plt

names = [3500, 0, 10, 20, 30, 40, 50, 67]
ticks = [1,2,3,4,5,6,7,8]
with open('query-exp/xlabels.pkl', 'rb') as fi:
    x = pickle.load(fi)
with open('query-exp/rev-labels.pkl', 'rb') as fi:
    revs = pickle.load(fi)
data = []

labels = [f'{a} /\n{b}' for a,b in zip(revs, x)]
means = []
for n in names:
    print(n)
    with open(f'query-exp/time-{n}.pkl', 'rb') as fi:
        l = pickle.load(fi)
    data.append(l)

plt.boxplot(data)
plt.xticks(ticks, labels)
plt.ylabel('Query time [s]')
plt.xlabel('Size of database [#revisions / #triples]')
plt.subplots_adjust(bottom=0.15)
plt.show()