# RIMBO demonstration
Example showing how a database with revisions to biological models can be created, based on the [RIMBO ontology](https://github.com/filipkro/rimbo).

`./query-exp` contain data generating the box plot figure in the paper. The data was generated running `query_times.py` and plotted using `plot_times.py`.
The code generating the example knowledge graph can be found in `gen_parallel_db.py`, `gen_serial_db.py`, and `graph_utils.py`.
`query_counts.py` queries for number of revisions and number of different revisions.
`get_model.py` contains an example of how the SBML model can be recreated from a query.

Knowledge graphs of different size and some of the generated models are available https://chalmers-my.sharepoint.com/:f:/g/personal/filipkro_chalmers_se/EnaN4zOCQytNhOuXeZlP1OUBCNDk58lFUFewJobNqDLSiA?e=oyxXvo.

[here](﻿﻿﻿﻿https://chalmers-my.sharepoint.com/:f:/g/personal/filipkro_chalmers_se/EnaN4zOCQytNhOuXeZlP1OUBCNDk58lFUFewJobNqDLSiA?e=oyxXvo).
﻿﻿﻿﻿https://chalmers-my.sharepoint.com/:f:/g/personal/filipkro_chalmers_se/EnaN4zOCQytNhOuXeZlP1OUBCNDk58lFUFewJobNqDLSiA?e=oyxXvo
The code runs with Python 3.10.11, and the requirements can be installed by running 
```
pip install -r requirements.txt
```
