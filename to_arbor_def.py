import dbbs_models, itertools

cable_props = ("ra", "cm")
ions = ("k", "na", "h", "ca", "cl")
ion_prefix = ("e",)
ion_props = dict()
for i in ions:
    for p in ion_prefix:
        ion_props[p + i] = (i, p)
print(ion_props)
for k, v in dbbs_models.__dict__.items():
    if not k.endswith("BasketCell"):
        continue
    print("---", k, "converter ---")
    defs = v.section_types
    m = dict()
    for sec_type, old_def in defs.items():
        nw = dict(
            cable={}, ions={}, mechanisms={m: {} for m in old_def.get("mechanisms", ())}
        )
        if "synapses" in old_def:
            nw["synapses"] = old_def["synapses"]
        for attr_name, val in old_def.get("attributes", {}).items():
            if isinstance(attr_name, str):
                prop = ion_props.get(attr_name, None)
                if prop:
                    ion_dict = nw["ions"].setdefault(prop[0], {})
                    ion_dict[prop[1]] = val
                elif attr_name.lower() in cable_props:
                    nw["cable"][attr_name] = val
                else:
                    raise Exception(
                        f"Couldn't convert {attr_name} to anything sensible."
                    )
            elif isinstance(attr_name, tuple):
                mech_dict = nw["mechanisms"].setdefault(attr_name[1], {})
                mech_dict[attr_name[0]] = val
            else:
                raise Exception(f"Couldn't convert {attr_name} to anything sensible.")
        m[sec_type] = nw

    print(m)
