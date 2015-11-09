from app.readers import tsv as reader
from app.readers import fasta
from app.dataformats import prottable as prottabledata
from app.dataformats import mzidtsv as mzidtsvdata 


TARGET = 't'
DECOY = 'd'


def write_pick_td_tables(target, decoy, theader, dheader,
                         targetfasta, decoyfasta, inferencetype):
    tfile, dfile = 'target.txt', 'decoy.txt'
    tdmap = {}
    header = '{}\t{}'.format(prottabledata.HEADER_PROTEIN,
                             prottabledata.HEADER_QSCORE)
    with open(tfile, 'w') as tdmap[TARGET], open(dfile, 'w') as tdmap[DECOY]:
        tdmap[TARGET].write(header)
        tdmap[DECOY].write(header)
        for pdata in generate_pick_fdr(target, decoy, theader, dheader,
                                       targetfasta, decoyfasta, inferencetype):
            ptype, protein, score = pdata
            tdmap[ptype].write('\n{}\t{}'.format(protein, score))
    return tfile, dfile


def generate_pick_fdr(targetprot, decoyprot, theader, dheader,
                      targetfasta, decoyfasta, picktype):
    t_scores, d_scores = generate_scoremaps(targetprot, decoyprot,
                                            theader, dheader)
    if picktype == 'fasta':
        tdmap = create_td_gene_map(targetfasta, decoyfasta)
    elif picktype == 'result':
        tdmap = create_td_assoc_map(targetprot, decoyprot, theader, dheader)
    td_picked = generate_picked_genes(tdmap, t_scores, d_scores)
    for ptype, pickedprotein, score in td_picked:
        yield ptype, pickedprotein, score


def generate_picked_genes(tdmap, tscores, dscores):
    for tgene, dgene in tdmap.items():
        tscore, dscore = tscores.get(tgene), dscores.get(dgene)
        picked = pick_target_decoy(tgene, dgene, tscore, dscore)
        if picked:
            p_type, pickedgene, score = picked
            yield p_type, pickedgene, score


def get_score(protein):
    return protein[prottabledata.HEADER_QSCORE]


def create_td_gene_map(tfastafn, dfastafn):
    tfasta = (x[1] for x in fasta.get_proteins_genes(tfastafn))
    dfasta = (x[1] for x in fasta.get_proteins_genes(dfastafn))
    return create_td_map(tfasta, dfasta)


def create_td_assoc_map(tproteins, dproteins, theader, dheader):
    tdmap = {}
    for dprot in reader.generate_tsv_proteins(dproteins, dheader):
        dprot = dprot[prottabledata.HEADER_PROTEIN]
        faketprot = dprot.replace(mzidtsvdata.DECOY_PREFIX, '')
        tdmap[faketprot] = dprot
    for tprot in reader.generate_tsv_proteins(tproteins, theader):
        tprot = tprot[prottabledata.HEADER_PROTEIN]
        if not tdmap.get(tprot, False):
            tdmap[tprot] = None
    return tdmap


def create_td_protein_map(tfastafn, dfastafn):
    tfasta = fasta.generate_proteins_id(tfastafn)
    dfasta = fasta.generate_proteins_id(dfastafn)
    return create_td_map(tfasta, dfasta)


def create_td_map(tfasta, dfasta):
    tdmap = {}
    for target, decoy in zip(tfasta, dfasta):
        tdmap[target] = decoy
    return tdmap


def create_content_master_map(prottable, header):
    contentmap = {}
    for protein in reader.generate_tsv_proteins(prottable, header):
        master = protein[prottabledata.HEADER_PROTEIN]
        content = reader.get_content_proteins_from_master(protein)
        contentmap.update({prot: master for prot in content})


def generate_scoremaps(targetprot, decoyprot, theader, dheader):
    t_scores, d_scores = {}, {}
    for protein in reader.generate_tsv_proteins(targetprot, theader):
        t_scores[protein[prottabledata.HEADER_PROTEIN]] = get_score(protein)
    for protein in reader.generate_tsv_proteins(decoyprot, dheader):
        d_scores[protein[prottabledata.HEADER_PROTEIN]] = get_score(protein)
    return t_scores, d_scores


def pick_target_decoy(target, decoy, tscore, dscore):
    """Feed it with a target and decoy score and the protein/gene/id names,
    and this will return target/decoy type, the winning ID and the score"""
    try:
        tscore = float(tscore)
    except (ValueError, TypeError):
        tscore = False
    try:
        dscore = float(dscore)
    except (ValueError, TypeError):
        dscore = False
    if tscore > dscore:
        return TARGET, target, tscore
    elif tscore < dscore:
        return DECOY, decoy, dscore
    else:
        return False
