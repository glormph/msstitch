from app.drivers.pycolator.qvality import QvalityDriver
from app.actions.prottable import qvality as preparation
from app.readers import tsv


class ProttableQvalityDriver(QvalityDriver):
    def __init__(self, **kwargs):
        super(ProttableQvalityDriver).__init__(**kwargs)
        self.score_get_fun = preparation.prepare_qvality_input
        if '***reverse' not in self.qvalityoptions:
            self.qvalityoptions.extend(['***reverse'])

    def set_features(self):
        targetheader = tsv.get_tsv_header(self.fn)
        self.target = tsv.generate_tsv_proteins(self.fn, targetheader)
        decoyheader = tsv.get_tsv_header(self.decoy)
        self.decoy = tsv.generate_tsv_proteins(self.decoy, decoyheader)
        super().set_features()