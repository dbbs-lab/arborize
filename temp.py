import logging

import bluepyopt as bpop
import bluepyopt.ephys as ephys
import dbbs_models
from bsb.morphologies import parse_morphology_file

from arborize import define_constraints
from arborize.optimizers._bluepyopt import get_bpo_cell
from arborize.schematics import bsb_schematic


logging.getLogger().setLevel(logging.DEBUG)


def create_schema(constraints, tags, file_morphology):
    _m = parse_morphology_file(file_morphology, tags=tags)
    return bsb_schematic(_m, constraints)


schema = create_schema(
    define_constraints(
        {
            "synapse_types": {
                ("AMPA", "granule"): {
                    "tau_facil": 5,
                    "tau_rec": 8,
                    "tau_1": 1,
                    "gmax": 140000,
                    "U": 0.43,
                },
                ("NMDA", "granule"): {
                    "tau_facil": 5,
                    "tau_rec": 8,
                    "tau_1": 1,
                    "gmax": 23500,
                    "U": 0.43,
                },
                ("GABA", "granule"): {"U": 0.35},
            },
            "cable_types": {
                "soma": {
                    "cable": {"Ra": 100, "cm": 2},
                    "ions": {"k": {"rev_pot": -80.993}, "ca": {"rev_pot": 137.5}},
                    "mechanisms": {
                        "Leak": {
                            "e": -60,
                            "gmax": [0.00029038073716, 0.00029038073717],
                        },
                        "Kv3_4": {"gkbar": 0.00076192450952},
                        "Kv4_3": {"gkbar": 0.00281496839061},
                        "Kir2_3": {"gkbar": 0.00074725514702},
                        "Ca": {"gcabar": 0.00060938071784},
                        "Kv1_1": {"gbar": 0.00569738264555},
                        "Kv1_5": {"gKur": 0.00083407556714},
                        "Kv2_2": {"gKv2_2bar": 1.203410852e-05},
                        ("cdp5", "CR"): {},
                    },
                },
                "dendrites": {
                    "cable": {"Ra": 100, "cm": 2.5},
                    "ions": {"k": {"rev_pot": -80.993}, "ca": {"rev_pot": 137.5}},
                    "mechanisms": {
                        "Leak": {"e": -60, "gmax": 0.00025029700737},
                        ("Leak", "GABA"): {},
                        "Ca": {"gcabar": 0.00500128008459},
                        "Kca1_1": {"gbar": 0.01001807454651},
                        "Kv1_1": {"gbar": 0.00381819207934},
                        ("cdp5", "CR"): {},
                    },
                },
                "axon": {"cable": {}, "ions": {}, "mechanisms": {}},
                "ascending_axon": {
                    "cable": {"Ra": 100, "cm": 1},
                    "ions": {
                        "na": {"rev_pot": 87.39},
                        "k": {"rev_pot": -80.993},
                        "ca": {"rev_pot": 137.5},
                    },
                    "mechanisms": {
                        ("Na", "granule_cell"): {"gnabar": 0.02630163681502},
                        "Kv3_4": {"gkbar": 0.00237386061632},
                        "Leak": {"e": -60, "gmax": 9.364092125e-05},
                        "Ca": {"gcabar": 0.00068197420273},
                        ("cdp5", "CR"): {},
                    },
                },
                "parallel_fiber": {
                    "cable": {"Ra": 100, "cm": 1},
                    "ions": {
                        "na": {"rev_pot": 87.39},
                        "k": {"rev_pot": -80.993},
                        "ca": {"rev_pot": 137.5},
                    },
                    "mechanisms": {
                        ("Na", "granule_cell"): {"gnabar": 0.01771848449261},
                        "Kv3_4": {"gkbar": 0.00817568047037},
                        "Leak": {"e": -60, "gmax": 3.5301616e-07},
                        "Ca": {"gcabar": 0.0002085683353},
                        ("cdp5", "CR"): {},
                    },
                },
                "axon_initial_segment": {
                    "cable": {"Ra": 100, "cm": 1},
                    "ions": {
                        "na": {"rev_pot": 87.39},
                        "k": {"rev_pot": -80.993},
                        "ca": {"rev_pot": 137.5},
                    },
                    "mechanisms": {
                        ("Na", "granule_cell_FHF"): {"gnabar": 1.28725006737226},
                        "Kv3_4": {"gkbar": 0.00649595340654},
                        "Leak": {"e": -60, "gmax": 0.00029276697557},
                        "Ca": {"gcabar": 0.00031198539472},
                        "Km": {"gkbar": 0.00056671971737},
                        ("cdp5", "CR"): {},
                    },
                },
                "axon_hillock": {
                    "cable": {"Ra": 100, "cm": 2},
                    "ions": {
                        "na": {"rev_pot": 87.39},
                        "k": {"rev_pot": -80.993},
                        "ca": {"rev_pot": 137.5},
                    },
                    "mechanisms": {
                        "Leak": {"e": -60, "gmax": 0.0003695818972},
                        ("Na", "granule_cell_FHF"): {"gnabar": 0.00928805851462},
                        "Kv3_4": {"gkbar": 0.02037346310915},
                        "Ca": {"gcabar": 0.00057726155447},
                        ("cdp5", "CR"): {},
                    },
                },
            },
        },
        use_defaults=True,
    ),
    {
        16: ["axon", "axon_hillock"],
        17: ["axon", "axon_initial_segment"],
        18: ["axon", "ascending_axon"],
        19: ["axon", "parallel_fiber"],
    },
    r"/home/robin/git/single_cell_test/dbbs_model_test/Granule_cell/morphology/GranuleCell.swc",
)
cell = get_bpo_cell(
    schema,
    debug=create_schema(
        dbbs_models.GranuleCellModel,
        {
            16: ["axon", "axon_hillock"],
            17: ["axon", "axon_initial_segment"],
            18: ["axon", "ascending_axon"],
            19: ["axon", "parallel_fiber"],
        },
        r"/home/robin/git/single_cell_test/dbbs_model_test/Granule_cell/morphology/GranuleCell.swc",
    ),
)

soma_loc = ephys.locations.NrnSeclistCompLocation(
    name="soma", seclist_name="soma", sec_index=0, comp_x=0.5
)

NUMBER_INDIVIDUALS = 1  # Number of individuals in offspring
NUMBER_GENERATIONS = 1  # Maximum number of generations

sweep_protocols = []
for protocol_name, amplitude in [
    # ("step1", 0.01),
    ("step2", 0.016),
    # ("step3", 0.022),
]:
    stim = ephys.stimuli.NrnSquarePulse(
        step_amplitude=amplitude,
        step_delay=100,
        step_duration=100,
        location=soma_loc,
        total_duration=200,
    )
    rec = ephys.recordings.CompRecording(
        name="%s.soma.v" % protocol_name, location=soma_loc, variable="v"
    )
    protocol = ephys.protocols.SweepProtocol(protocol_name, [stim], [rec])
    sweep_protocols.append(protocol)
threestep_protocol = ephys.protocols.SequenceProtocol(
    "twostep", protocols=sweep_protocols
)

# NEURON sim
nrn = ephys.simulators.NrnSimulator(dt=0.025, cvode_active=False)

# feature of obj function
efel_feature_means = {
    "step1": {
        "AP_height": 20.93,
        "ISI_CV": 0.261,
        "AHP_depth_abs_slow": -52.69,
        "AP_width": 0.665,
        "voltage_base": -68.5,
        "AHP_depth_abs": -59.21,
        "time_to_first_spike": 31.9,
        "adaptation_index2": 0.1062,
        "mean_frequency": 25,
    },
    "step2": {
        "AP_height": 19.255,
        "ISI_CV": 0.14,
        "AHP_depth_abs_slow": -48.935,
        "AP_width": 0.695,
        "voltage_base": -68.77,
        "AHP_depth_abs": -58.3,
        "time_to_first_spike": 19.0,
        "adaptation_index2": 0.034,
        "mean_frequency": 40,
    },
    "step3": {
        "AP_height": 17.645,
        "ISI_CV": 0.148,
        "AHP_depth_abs_slow": -32.67,
        "AP_width": 0.7135,
        "voltage_base": -69.125,
        "AHP_depth_abs": -57.191,
        "time_to_first_spike": 14.65,
        "adaptation_index2": 0.029,
        "mean_frequency": 50,
    },
}

# obj function
objectives = []
for protocol in sweep_protocols:
    stim_start = protocol.stimuli[0].step_delay
    stim_end = stim_start + protocol.stimuli[0].step_duration
    for efel_feature_name, mean in efel_feature_means[protocol.name].items():
        feature_name = "%s.%s" % (protocol.name, efel_feature_name)
        feature = ephys.efeatures.eFELFeature(
            feature_name,
            efel_feature_name=efel_feature_name,
            recording_names={"": "%s.soma.v" % protocol.name},
            stim_start=stim_start,
            stim_end=stim_end,
            exp_mean=mean,
            exp_std=0.1 * mean,
        )
        objective = ephys.objectives.SingletonObjective(feature_name, feature)
        objectives.append(objective)
score_calc = ephys.objectivescalculators.ObjectivesCalculator(objectives)

print([(p.name, p.frozen) for p in cell.params.values()])
# cell evaluator
cell_evaluator = ephys.evaluators.CellEvaluator(
    cell_model=cell,
    param_names=[p.name for p in cell.params.values() if not p.frozen],
    fitness_protocols={threestep_protocol.name: threestep_protocol},
    fitness_calculator=score_calc,
    sim=nrn,
)

# opt
optimisation = bpop.optimisations.DEAPOptimisation(
    evaluator=cell_evaluator,
    offspring_size=NUMBER_INDIVIDUALS,
    seed=333,
)

# final_pop, hall_of_fame, logs, hist = optimisation.run(max_ngen=NUMBER_GENERATIONS)

# best individual
# best_ind = hall_of_fame[0]
# print("Best individual: ", best_ind)
# print("Fitness values: ", best_ind.fitness.values)
#
# best_ind_dict = cell_evaluator.param_dict(best_ind)
# print("Ind dict", best_ind_dict)
responses = threestep_protocol.run(
    cell_model=cell,
    param_values={"gmax_glia__dbbs__Leak__0_soma": 0.00029038073716554835},
    sim=nrn,
    isolate=False,
)

import plotly.graph_objs as go

go.Figure(
    [
        go.Scatter(x=resp["time"], y=resp["voltage"], name=name)
        for name, resp in responses.items()
    ]
).write_html("gpop.html")
