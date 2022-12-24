from arborize import define_model

empty = define_model({})
pas = define_model(
    {
        "cable_types": {
            "soma": {
                "cable": {"Ra": 10},
                "mechanisms": {"pas": {"e": -70, "g": 0.01}},
            },
            "apical_dendrite": {
                "cable": {"Ra": 10},
            },
            "basal_dendrite": {
                "cable": {"Ra": 10},
            },
        }
    }
)
expsyn = define_model(
    {
        "cable_types": {
            "soma": {
                "cable": {"Ra": 10},
                "synapses": {
                    "ExpSyn": {
                        "tau": 2
                    }
                },
            },
        },
        "synapse_types": {
            "expsyn2": {
                "mechanism": "ExpSyn",
                "parameters": {
                    "tau": 3
                }
            }
        }
    },
    use_defaults=True
)
