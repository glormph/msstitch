import os
import subprocess

from app.preparation import mzidplus as prep
from app.writers import tsv as writers


class BaseDriver(object):
    def __init__(self, **kwargs):
        self.outdir = kwargs['outdir']

    def create_outfilepath(self, fn, suffix=None):
        basefn = os.path.basename(fn)
        outfn = basefn + suffix
        return os.path.join(self.outdir, outfn)


class MzidPercoTSVDriver(BaseDriver):
    def __init__(self, **kwargs):
        super(MzidPercoTSVDriver, self).__init__(**kwargs)
        self.idfn = kwargs.get('ids', None)
        self.multipsm_per_scan = kwargs.get('allpsms', False)
        assert self.idfn is not None

    def run(self):
        self.get_psms()
        self.write()

    def get_psms(self, quantdb):
        """Runs MSGF+ mzid2tsv converter to create table on mzid file.
        Then adds percolator data from mzid file to table.
        """
        mzidtsv = 'mzid.tsv'
        subprocess.call(['java', '-Xmx3500M', '-cp', 'MSGFPlus.jar',
                         'edu.ucsd.msjava.ui.MzIDToTsv', '-i', self.idfn,
                         '-o', mzidtsv])
        if self.multipsm_per_scan is True:
            # FIXME not supported yet
            # Create mzid PSM/sequence sqlite (fn, scan, rank, sequence)
            pass
        else:
            seqlookup = None

        self.header = prep.get_header_from_mzidtsv(mzidtsv,
                                                   self.multipsm_per_scan)
        self.psms = prep.add_percolator_to_mzidtsv(self.idfn,
                                                   mzidtsv,
                                                   self.multipsm_per_scan,
                                                   seqlookup)

    def write(self):
        outfn = self.create_outfilepath('percomzid.tsv')
        writers.write_tsv(self.header, self.psms, outfn)