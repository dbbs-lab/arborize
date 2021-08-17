from bsb.output import MorphologyRepository
import dbbs_models, itertools

mr = MorphologyRepository("morphos.hdf5")
# mr.import_arbz_module(dbbs_models)
gc = mr.get_morphology("PurkinjeCell")

tags = ["soma", "axon", "dendrites"]
structure_id = dict(zip(tags, (1, 2, 3)))
comp_id = itertools.count()

def write_branch(file, branch, connector):
    sid = structure_id[branch._full_labels[0]]
    parent = connector
    for x, y, z, r in branch.walk():
        id = next(comp_id)
        file.write(" ".join(map(str, (id, sid, x, y, z, r, parent))) + "\n")
        parent = id
    for child in branch._children:
        write_branch(file, child, connector=parent)


with open("purkinje_cell.swc", "w") as f:
    for root in gc.roots:
        write_branch(f, root, connector=-1)
