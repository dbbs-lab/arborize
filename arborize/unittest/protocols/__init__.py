from ._protocol import TestProtocol
from patch import p

class Autorhythm(TestProtocol):
    def prepare(self):
        def init_simulator(dt=0.025, celsius=32, tstop=1000, v_init=-70):
            for k, v in vars().items():
                setattr(p, k, v)

        def disable_cvode():
            time_step = p.CVode()
            time_step.active(0)

        init_simulator()
        disable_cvode()

        # for chief in self.setup.chiefs:
        self._vm = cell.record_soma()
        self._time = p.time

    def run(self):
        p.finitialize()
        p.run()

    def results(self):
        # e = ezfel(T=list(_time), signal=list(_vm))
        #
        # # Create a build artifact
        # VoltageTrace(
        #     cell,
        #     "Autorhythm",
        #     _time,
        #     _vm,
        #     duration=duration,
        #     frequency=list(e.inv_second_ISI),
        # )
        #
        # return e
        return list(self._vm), list(self._t)
