from app.readers import mzidplus as readers
from app.readers import tsv as tsvreader


def merge_mzidtsvs(fns, header):
    for fn in fns:
        if header != tsvreader.get_tsv_header(fn):
            raise RuntimeError('Headers of TSV files to concatenate are '
                               'not identical')
    return readers.generate_tsv_lines_multifile(fns)


def get_percoline(specresult, namespace, line, multipsm, seqdb):
    """Extracts percolator data from specresult and returns a dict"""
    out = line
    out.update({'rank': None})
    try:
        xmlns = '{%s}' % namespace['xmlns']
    except TypeError:
        xmlns = ''
    if multipsm is True:
        pass  # FIXME support later
        # loop through psms in specresult
        # check line sequence (without mods) in seqdb with psm
        # get percodata,
        # percoline = [line-with-correct-rank]
    else:  # only the first element
        perco = readers.get_specidentitem_percolator_data(
            specresult.find('{0}SpectrumIdentificationItem'.format(xmlns)),
            namespace)
    out.update(perco)
    return out


def get_specresult_data(specresults, id_fnlookup):
    specresult = next(specresults)
    scannr = readers.get_specresult_scan_nr(specresult)
    mzmlid = readers.get_specresult_mzml_id(specresult)
    return specresult, {'scan': scannr, 'fn': id_fnlookup[mzmlid]}


def add_percolator_to_mzidtsv(mzidfn, tsvfn, multipsm, header, seqdb=None):
    """Takes a MSGF+ tsv and corresponding mzId, adds percolatordata
    to tsv lines. Generator yields the lines. Multiple PSMs per scan
    can be delivered, in which case rank is also reported.
    """
    namespace = readers.get_mzid_namespace(mzidfn)
    specfnids = readers.get_mzid_specfile_ids(mzidfn, namespace)
    specresults = readers.mzid_spec_result_generator(mzidfn, namespace)
    with open(tsvfn) as mzidfp:
        # skip header
        oldheader = next(mzidfp)
        # multiple lines can belong to one specresult, so we use a nested
        # for/while-true-break construction.
        writelines = []
        specresult, specdata = get_specresult_data(specresults, specfnids)
        for line in mzidfp:
            line = {x: y for x, y in zip(oldheader, line.split('\t'))}
            while True:
                if writelines and not multipsm:
                    # Only keep best ranking psm
                    # FIXME we assume best ranking is first line. Fix this in
                    # future
                    yield writelines
                    writelines = []
                    break
                # FIXME get header names instead of positions!
                if line[oldheader[2]] == specdata['scan'] \
                   and line[oldheader[0]] == specdata['fn']:
                    # add percolator stuff to line
                    outline = get_percoline(specresult, namespace, line,
                                            multipsm, seqdb)
                    writelines.append(outline)
                    break  # goes to next line in tsv
                else:
                    yield writelines
                    writelines = []
                    specresult, specdata = get_specresult_data(specresults,
                                                               specfnids)
        # write last line
        yield writelines


def get_header_with_percolator(fn, multipsm=False):
    header = get_header_from_mzidtsv(fn)
    if multipsm is True:
        # FIXME should this be here???
        header.append('rank')
    header.extend(readers.PERCO_HEADER)
    return header


def get_header_from_mzidtsv(fn):
    with open(fn) as fp:
        line = next(fp)
    return line.split('\t')
