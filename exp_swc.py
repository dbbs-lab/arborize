from bsb.output import MorphologyRepository
import dbbs_models, itertools, sys

mr = MorphologyRepository("morphos.hdf5")
for morfo in sys.argv[1:]:
    m = mr.get_morphology(morfo)

    tags = ["soma", "axon", "dendrites"]
    structure_id = dict(zip(tags, (1, 2, 3)))
    ntag = 16
    comp_id = itertools.count()
    tags = dict()

    def get_sid(labels):
        global ntag, tags
        label_set = "__".join(sorted(set(labels)))
        sid = structure_id.get(label_set)
        if sid is None:
            structure_id[label_set] = sid = ntag
            tags[ntag] = labels
            ntag += 1
        return sid


    def write_branch(file, branch, connector):
        sid = get_sid(branch._full_labels)
        parent = connector

        for x, y, z, r in branch.walk():
            id = next(comp_id)
            file.write(" ".join(map(str, (id, sid, x, y, z, r, parent))) + "\n")
            parent = id
        for child in branch._children:
            write_branch(file, child, connector=parent)


    with open(f"{morfo}.swc", "w") as f:
        print("------------")
        print(f"Starting {morfo}")
        print("------------")
        for root in m.roots:
            write_branch(f, root, connector=-1)
        print("tag_translations = {")
        for k, v in tags.items():
            print(" ", f"{k}: {v},")
        print("}")
