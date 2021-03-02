from ._protocol import TestProtocol
from patch import p
from .. import Results
from .._helpers import ezfel

class Autorhythm(TestProtocol):
    def __init__(self, dur=300, skip=0, *, freq=None):
        super().__init__()
        self.freq = freq
        self.skip = skip
        self.duration = dur

    def prepare(self, setup):
        def init_simulator(dt=0.025, celsius=32, tstop=self.duration, v_init=-70):
            for k, v in vars().items():
                setattr(p, k, v)

        def disable_cvode():
            time_step = p.CVode()
            time_step.active(0)

        init_simulator()
        disable_cvode()

        self._time = p.time
        for name, subject in setup.subjects.items():
            subject.record_soma()

    def run(self):
        p.finitialize()
        p.run()

    def results(self, test):
        results = Results()
        for name, subject in test.setup.subjects.items():
            t = list(self._time)
            first_sample = 0
            for x, tx in enumerate(t):
                first_sample = x
                if tx >= self.skip:
                    break
            t, Vm = t[first_sample:], list(subject.Vm)[first_sample:]
            e = ezfel(T=t, signal=Vm)
            # Create a build artifact
            # VoltageTrace(
            #     cell,
            #     "Autorhythm",
            #     self._time,
            #     subject.Vm,
            #     duration=duration,
            #     frequency=list(e.inv_second_ISI),
            # )
            results.set(e, name=f"{name}.vm")
            import plotly.graph_objs as go

            go.Figure(go.Scatter(x=t, y=Vm)).show()
            test.assertAlmostEqual(self.freq, 1000 * e.Spikecount[0]  / (t[-1] - t[0]))
        return results
