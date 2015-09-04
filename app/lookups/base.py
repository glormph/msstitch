from app.lookups.sqlite import (proteingroups, quant, searchspace,
                                biosets, spectra, prottable, psms)


def get_lookup(fn, lookuptype):
    lookupmap = {'biosets': biosets.BioSetDB,
                 'spectra': spectra.SpectraDB,
                 'psm': psms.PSMDB,
                 'proteingroups': proteingroups.ProteinGroupDB,
                 'quant': quant.QuantDB,
                 'isoquant': quant.IsobaricQuantDB,
                 'ms1quant': quant.PrecursorQuantDB,
                 'searchspace': searchspace.SearchSpaceDB,
                 'peptidetable': prottable.PepTableDB,
                 'prottable': prottable.ProtTableDB,
                 }
    return lookupmap[lookuptype](fn)


def create_new_lookup(fn, lookuptype):
    with open(fn, 'w'):
        pass
    return get_lookup(fn, lookuptype)
