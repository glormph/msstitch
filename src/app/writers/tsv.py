def write_tsv(headerfields, features, outfn):
    """Writes header and generator of lines to tab separated file.

    headerfields - list of field names in header in correct order
    features - generates 1 list per line that belong to header
    outfn - filename to output to. Overwritten if exists
    """
    with open(outfn, 'w') as fp:
        write_tsv_line_from_list(headerfields, fp)
        for line in features:
            write_tsv_line_from_list([str(line[field]) for field
                                      in headerfields], fp)


def write_multi_mzidtsv(header, oldheader, psms, base_outfile):
    outfile_handles = {}
    for psm in psms:
        line = psm['psm']
        split_pool = psm['split_pool']
        if split_pool not in outfile_handles:
            outfile_handles[split_pool] = open(base_outfile.format(split_pool),
                                               'w')
            write_tsv_line_from_list(header, outfile_handles[split_pool])
        write_tsv_line_from_list([line[field] for field in oldheader],
                                     outfile_handles[split_pool])
    [handle.close() for handle in outfile_handles.values()]


def write_tsv_line_from_list(linelist, outfp):
    """Utility method to convert list to tsv line with carriage return"""
    line = '\t'.join(linelist)
    outfp.write(line)
    outfp.write('\n')


def parse_NA(feature, header):
    for field in header:
        try:
            feature[field] = str(feature[field])
        except KeyError:
            feature[field] = 'NA'
    return feature


def write_prottable_with_na(header, psms, outfn):
    na_psms = (tsv.parse_NA(x, header) for x in psms)
    write_tsv(header, na_psms, outfn)
