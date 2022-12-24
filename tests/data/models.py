from arborize import define_model

empty = define_model({})
Kca1_1 = define_model({
    "cable_types": {
        "soma": {
            "cable": {"Ra": 10}
        }
    }
})