from app.drivers.mslookup import base
from app.readers import openms as openmsreader
from app.actions.mslookup import quant as lookups


class QuantLookupDriver(base.LookupDriver):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spectrafns = kwargs.get('spectra', None)  # not for all lookups


class IsobaricQuantLookupDriver(QuantLookupDriver):
    lookuptype = 'isobaricquant'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cons_fns = self.fn

    def create_lookup(self):
        quantmap = openmsreader.get_quantmap(self.cons_fns[0])
        mzmlfn_consxml = openmsreader.mzmlfn_cons_el_generator(self.spectrafns,
                                                               self.cons_fns)
        lookups.create_isobaric_quant_lookup(self.lookup, mzmlfn_consxml,
                                             quantmap),


class PrecursorQuantLookupDriver(QuantLookupDriver):
    lookuptype = 'ms1quant'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.precursorfns = self.fn

    def create_lookup(self):
        specfn_feats = openmsreader.mzmlfn_feature_generator(self.spectrafns,
                                                             self.precursorfns)
        lookups.create_precursor_quant_lookup(self.lookup, specfn_feats)