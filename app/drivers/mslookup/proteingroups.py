from app.actions.mslookup import proteingrouping as lookups
from app.drivers.mslookup import base


class ProteinGroupLookupDriver(base.LookupDriver):
    lookuptype = 'proteingroups'
    command = 'proteingroup'
    commandhelp = ('Groups proteins from mzid2tsv output (single file '
                   'passed to -i)')

    def create_lookup(self):
        lookups.build_proteingroup_db(self.lookup)
