from errr.tree import make_tree as _make_tree, exception as _e

_make_tree(globals(),
    ArborizeError=_e(
        ConnectionError=_e(
            AmbiguousSynapseError=_e(),
            SynapseNotPresentError=_e(),
            SynapseNotDefinedError=_e(),
        ),
        ModelError=_e(
            ModelClassError=_e(
                MechanismNotPresentError=_e("mechanism"),
                MechanismNotFoundError=_e("mechanism", "variant"),
                LabelNotDefinedError=_e(),
                SectionAttributeError=_e(),
            ),
            MorphologyBuilderError=_e(),
        ),
    ),
)
