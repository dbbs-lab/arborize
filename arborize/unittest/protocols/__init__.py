from ._protocol import TestProtocol
from patch import p
from .. import Results
from .._helpers import ezfel

def _skip_to(t, t0):
    f = 0
    for x, tx in enumerate(t):
        f = x
        if tx >= t0:
            break
    return f


class Autorhythm(TestProtocol):
    def __init__(self, dur=300, skip=0, *, freq=None):
        super().__init__()
        self.freq = freq
        self.skip = skip
        self.duration = dur

    def prepare(self, setup):
        setup.init_simulator(tstop=self.duration)
        setup.disable_cvode()

        self._time = p.time
        for name, subject in setup.subjects.items():
            subject.record_soma()

    def run(self):
        p.finitialize()
        p.run()

    def results(self, setup):
        results = Results()
        for name, subject in setup.subjects.items():
            t = list(self._time)
            first_sample = _skip_to(t, self.skip)
            t, Vm = t[first_sample:], list(subject.Vm)[first_sample:]
            e = ezfel(T=t, signal=Vm)
            f = 1000 * e.Spikecount[0]  / (t[-1] - t[0])
            results.set(f"{name}.vm", e)
            results.set(f"{name}.f", f)
        import plotly.graph_objs as go
        go.Figure(go.Scatter(x=t, y=Vm)).show()
        return results

    def asserts(self, test, results):
        for name, subject in test.setup.subjects.items():
            test.assertAlmostEqual(self.freq, results.get(f"{name}.f"))


class VoltageClamp(TestProtocol):
    def __init__(self, dur=400, skip=0, dur1=200, dur2=100, dur3=100, rec_offset=0, holding=-70, step=-80):
        super().__init__()
        self.dur1 = dur1
        self.dur2 = dur2
        self.dur3 = dur3
        self.holding = holding
        self.step = step
        self.skip = skip
        self.duration = dur
        self._curr = {}
        self.rec_offset = rec_offset

    def prepare(self, setup):
        setup.disable_cvode()
        setup.init_simulator(tstop=self.duration)
        self._time = p.time

        for name, cell in setup.subjects.items():
            cell.record_soma()
            clamp = p.SEClamp(cell.soma[0])

            clamp.dur1 = self.dur1
            clamp.dur2 = self.dur2
            clamp.dur3 = self.dur3
            voltage = self.step
            try:
                voltage = iter(voltage)
            except TypeError:
                clamp.amp1 = self.holding
                clamp.amp2 = voltage
                clamp.amp3 = self.holding
                voltage = [self.holding, voltage, self.holding]
            else:
                voltage = list(voltage)
                clamp.amp1 = voltage[0]
                clamp.amp2 = voltage[1]
                clamp.amp3 = voltage[2]

            self._curr[name] = p.record(clamp._ref_i)
            self._voltage = voltage


    def run(self):
        p.finitialize()
        p.run()

    def results(self, setup):
        results = Results()
        t = list(self._time)
        t_prerec = _skip_to(t, self.dur1) - 1
        for name, subject in setup.subjects.items():
            i = list(self._curr[name])
            i_pre = i[t_prerec]
            t_rec = _skip_to(t, self.dur1 + self.dur2 - self.rec_offset) - 1
            i_rec = i[t_rec]
            di = i_rec - i_pre
            dv = self._voltage[1] - self._voltage[0]
            g = (di * 1e-9) / (dv * 1e-3) * 10e12
            e = ezfel(T=t, signal=list(subject.Vm))
            results.set(f"{name}.vm", e)
            results.set(f"{name}.dv", dv)
            results.set(f"{name}.i", i)
            results.set(f"{name}.di", di)
            results.set(f"{name}.g", g)
        return results

    def asserts(self, test, results):
        pass

class InputConductance(VoltageClamp):
    def __init__(self, *args, g=None, places=7, **kwargs):
        super().__init__(*args, **kwargs)
        self.places = places
        self.g = g

    def asserts(self, test, results):
        for name, subject in test.setup.subjects.items():
            test.assertAlmostEqual(self.g, results.get(f"{name}.g"), places=self.places)
