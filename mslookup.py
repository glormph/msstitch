#!/usr/bin/python3

import sys
from app.drivers.mslookup import (spectra, quant, proteingroups, biosets,
                                  proteinquant, pepquant, psms, seqspace)
from app.drivers import startup


drivers = [biosets.BioSetLookupDriver(),
           spectra.SpectraLookupDriver(),
           psms.PSMLookupDriver(),
           quant.IsobaricQuantLookupDriver(),
           quant.PrecursorQuantLookupDriver(),
           proteingroups.ProteinGroupLookupDriver(),
           pepquant.PeptideQuantLookupDriver(),
           proteinquant.ProteinQuantLookupDriver(),
           seqspace.SeqspaceLookupDriver(),
           ]
startup.start_msstitch(drivers, sys.argv)
