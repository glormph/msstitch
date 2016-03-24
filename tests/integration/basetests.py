import unittest
import subprocess
import os
import shutil
import sqlite3
import re
from lxml import etree
from tempfile import mkdtemp


class BaseTest(unittest.TestCase):
    testdir = 'tests'
    fixdir = os.path.join(testdir, 'fixtures')
    outdir = os.path.join(testdir, 'test_output')

    def setUp(self):
        self.infile = os.path.join(self.fixdir, self.infilename)
        os.makedirs(self.outdir, exist_ok=True)
        self.workdir = mkdtemp(dir=self.outdir)
        self.resultfn = os.path.join(self.workdir,
                                     self.infilename + self.suffix)

    def tearDown(self):
        shutil.rmtree(self.workdir)

    def get_std_options(self):
        cmd = [self.executable, self.command, '-d', self.workdir, '-i']
        if type(self.infile) != list:
            self.infile = [self.infile]
        cmd.extend(self.infile)
        return cmd

    def run_command(self, options=[]):
        cmd = self.get_std_options()
        cmd.extend(options)
        try:
            subprocess.check_output(cmd)
        except subprocess.CalledProcessError:
            print('Failed to run executable {}'.format(self.executable))
            raise
        return cmd

    def run_command_expect_error(self, options=[]):
        try:
            cmd = self.run_command(options)
        except subprocess.CalledProcessError:
            pass
        else:
            self.fail('Command {} should throw an error'.format(cmd))

    def get_values_from_db(self, dbfile, sql):
        db = sqlite3.connect(dbfile)
        return db.execute(sql)

    def seq_in_db(self, dbconn, seq, seqtype):
        comparator = '='
        if seqtype == 'ntermfalloff':
            comparator = ' LIKE '
            seq = '{0}%'.format(seq[::-1])
        seq = seq.replace('L', 'I')
        sql = ('SELECT EXISTS(SELECT seqs FROM known_searchspace WHERE '
               'seqs{0}? LIMIT 1)'.format(comparator))
        return dbconn.execute(sql, (seq,)).fetchone()[0] == 1

    def get_tsvheader(self, fn):
        with open(fn) as fp:
            return next(fp).strip('\n').split('\t')

    def tsv_generator(self, fn):
        header = self.get_tsvheader(fn)
        tsv = self.get_all_lines(fn)
        for line in tsv:
            yield {field: val for field, val in
                   zip(header, line.strip('\n').split('\t'))}

    def get_all_lines(self, fn):
        with open(fn) as fp:
            next(fp)
            for line in fp:
                yield line

    def get_xml_namespace(self, fn):
        root = self.get_root_el(fn)
        ns = {}
        for prefix in root.nsmap:
            separator = ':'
            nsprefix = prefix
            if prefix is None:
                nsprefix = ''
                separator = ''
            ns['xmlns{0}{1}'.format(separator, nsprefix)] = root.nsmap[prefix]
        return ns

    def get_root_el(self, fn):
        rootgen = etree.iterparse(fn, events=('start',))
        root = next(rootgen)[1]
        for child in root.getchildren():
            root.remove(child)
        return root

    def copy_db_to_workdir(self, dbfn):
        shutil.copy(os.path.join(self.fixdir, dbfn), self.resultfn)

    def get_float_or_na(self, value):
        try:
            return float(value)
        except ValueError:
            return value


class BaseTestPycolator(BaseTest):
    executable = 'msspercolator'
    infilename = 'percolator_out.xml'

    def get_psm_pep_ids_from_file(self, fn):
        contents = self.read_percolator_out(fn)
        return {'psm_ids': self.get_element_ids(contents['psms'],
                                                'psm_id', contents['ns']),
                'peptide_ids': self.get_element_ids(contents['peptides'],
                                                    'peptide_id',
                                                    contents['ns']),
                'psm_seqs': self.get_psm_seqs(contents['psms'],
                                              contents['ns'])
                }

    def read_percolator_out(self, fn):
        ns = self.get_xml_namespace(fn)['xmlns']
        contents = {'ns': ns, 'psms': [], 'peptides': []}
        xml = etree.iterparse(fn)
        for ac, el in xml:
            if el.tag == '{%s}psm' % ns:
                contents['psms'].append(el)
            elif el.tag == '{%s}peptide' % ns:
                contents['peptides'].append(el)
        return contents

    def get_element_ids(self, elements, id_attrib, ns):
        return [x.attrib['{%s}%s' % (ns, id_attrib)] for x in elements]

    def get_psm_seqs(self, psms, ns):
        return [pepseq.attrib['seq'] for pepseq in
                self.get_subelements(psms, 'peptide_seq', ns)]

    def get_svms(self, elements, ns):
        return [svm.text for svm in
                self.get_subelements(elements, 'svm_score', ns)]

    def get_qvals(self, elements, ns):
        return [qval.text for qval in
                self.get_subelements(elements, 'q_value', ns)]

    def get_peps(self, elements, ns):
        return [pep.text for pep in
                self.get_subelements(elements, 'pep', ns)]

    def get_subelements(self, elements, subel, ns):
        return [element.find('{%s}%s' % (ns, subel)) for element in elements]

    def strip_modifications(self, pep):
        return re.sub('\[UNIMOD:\d*\]', '', pep)


class MzidTSVBaseTest(BaseTest):
    executable = 'msspsmtable'
    infilename = 'mzidtsv.txt'

    def setUp(self):
        super().setUp()
        self.dbfile = os.path.join(self.fixdir, 'mzidtsv_db.sqlite')

    def rowify(self, records):
        row, rownr = [], 0
        for record in records:
            if record[0] == rownr:
                row.append(record)
            else:
                yield row
                row = [record]
                rownr += 1

    def check_results(self, checkfields, expected_values):
        for resultvals, exp_vals in zip(self.get_values(checkfields),
                                        expected_values):
            for resultval, expectval in zip(resultvals, exp_vals):
                self.assertEqual([str(x) if x is not None else 'NA'
                                  for x in expectval],
                                 [str(x) for x in resultval])

    def process_dbvalues_both(self, dbfile, sql, channel_fields, permfieldnrs,
                              permfieldnames):
        dbvals = self.get_values_from_db(dbfile, sql)
        outresults, rownr, permvals = [], 0, []
        for record in dbvals:
            if record[0] != rownr:
                for outresult in outresults:
                    yield outresult
                for pfname, pval in zip(permfieldnames, permvals):
                    yield (rownr, pfname, pval)
                if channel_fields != []:
                    outresults = [tuple([record[0]] +
                                        [record[x] for x in channel_fields])]
                permvals = [record[nr] for nr in permfieldnrs]
                rownr += 1
            else:
                permvals = [record[nr] for nr in permfieldnrs]
                if channel_fields != []:
                    result = [record[0]] + [record[x] for x in channel_fields]
                    outresults.append(tuple(result))

    def get_values(self, checkfields):
        with open(self.resultfn) as fp:
            header = next(fp).strip('\n').split('\t')
            fieldindices = [header.index(field) for field in checkfields]
            row = 0
            for line in fp:
                line = line.strip('\n').split('\t')
                if len(checkfields) > 1:
                    yield [(row, field, line[ix]) for field, ix in
                           zip(checkfields, fieldindices)]
                else:
                    yield [(row, line[ix]) for ix in fieldindices]
                row += 1


class MSLookupTest(BaseTest):
    executable = 'msslookup'
    base_db_fn = None
    suffix = ''

    def setUp(self):
        super().setUp()
        self.resultfn = os.path.join(self.workdir, 'mslookup_db.sqlite')
        if self.base_db_fn is not None:
            self.copy_db_to_workdir(self.base_db_fn)

    def run_command(self, options=None):
        if options is None:
            options = []
        if self.base_db_fn is not None:
            options.extend(['--dbfile', self.resultfn])
        super().run_command(options)


class PepProtableTest(BaseTest):
    def isoquant_check(self, isotable, acc_field):
        isoquant = {}
        accession = self.get_tsvheader(isotable)[0]
        for line in self.tsv_generator(isotable):
            acc = line.pop(accession)
            isoquant[acc] = line
        for line in self.tsv_generator(self.resultfn):
            [self.assertEqual(isoquant[line[acc_field]][ch], line[ch])
             for ch in isoquant[line[acc_field]]]

    def check_build_values(self, sql, fields, accession):
        expected = {}
        for rec in self.get_values_from_db(self.dbfile, sql):
            # skip multiple entries of e.g protein group per peptide
            # or gene per protein
            try:
                expected[rec[0]][rec[1]] = rec[2:]
            except KeyError:
                expected[rec[0]] = {rec[1]: rec[2:]}
        for line in self.tsv_generator(self.resultfn):
            acc = line[accession]
            if acc not in expected:
                continue
            for setname, pepvals in expected[acc].items():
                for val, field in zip(pepvals, fields):
                    self.assertEqual(str(val),
                                     line['{}_{}'.format(setname, field)])

    def check_built_isobaric(self, sql, accession):
        expected = {}
        for rec in self.get_values_from_db(self.dbfile, sql):
            try:
                expected[rec[0]][rec[1]][rec[2]] = rec[3:]
            except KeyError:
                try:
                    expected[rec[0]][rec[1]] = {rec[2]: rec[3:]}
                except KeyError:
                    expected[rec[0]] = {rec[1]: {rec[2]: rec[3:]}}
        for line in self.tsv_generator(self.resultfn):
            for setname, fields in expected[line[accession]].items():
                for field in fields:
                    setfield = '{}_{}'.format(setname, field)
                    exp_val = fields[field]
                self.assertEqual(line[setfield], str(exp_val[0]))
                try:
                    nr_psms = line['{} - # quanted PSMs'.format(setfield)]
                except KeyError:
                    pass
                    # FIXME currently no # PSMs in peptide table isoquant!
                else:
                    self.assertEqual(nr_psms, str(exp_val[1]))


class PeptableTest(PepProtableTest):
    executable = 'msspeptable'


class ProttableTest(PepProtableTest):
    executable = 'mssprottable'
    infilename = 'prottable.txt'

    def get_top_psms(self, fn, pepkey, valuekey, lowerbetter=False):
        top_vals = {}
        for psm in self.tsv_generator(fn):
            prot = psm['Master protein(s)']
            seq = psm[pepkey]
            try:
                value = float(psm[valuekey])
            except ValueError:
                continue
            if prot in top_vals and seq in top_vals[prot]:
                if lowerbetter and value > top_vals[prot][seq]:
                    continue
                elif not lowerbetter and value < top_vals[prot][seq]:
                    continue
            try:
                top_vals[prot][seq] = value
            except KeyError:
                top_vals[prot] = {seq: value}
        return top_vals

    def check_protein_data(self, centrictype):
        centric = {'proteincentric': 'pc', 'genecentric': 'gc',
                   'assoccentric': 'ac'}[centrictype]
        sql_map = {'pc': {'primary':
                          ['pgm', 'protein_acc', 'protein_group_master'],
                          'fields': ['g.gene_acc', 'aid.assoc_id',
                                     'pc.coverage'],
                          'joins':
                          ['JOIN genes AS g USING(protein_acc) ',
                           'JOIN associated_ids AS aid USING(protein_acc) ',
                           'JOIN protein_coverage AS pc USING(protein_acc)',
                           ]},
                   'gc': {'primary': ['g', 'gene_acc', 'genes'],
                          'fields': ['"NA"'] * 3,
                          'joins':
                          ['JOIN associated_ids USING(protein_acc) ',
                           ]},
                   'ac': {'primary': ['aid', 'assoc_id', 'associated_ids'],
                          'fields': ['"NA"'] * 3,
                          'joins':
                          ['JOIN genes USING(protein_acc) ',
                           ]},
                   }[centric]

        sql = ('SELECT {0}.{1}, {3}, {4}, pd.description, {5} '
               'FROM {2} AS {0} '
               '{6} '
               'JOIN prot_desc AS pd USING(protein_acc)')
        sql_adds = sql_map['primary'] + sql_map['fields']
        sql_adds.append(' '.join(sql_map['joins']))
        sql = sql.format(*sql_adds)
        psm_sql_map = {'pc': ('pgm', 'protein_acc', 'protein_group_master'),
                       'gc': ('g', 'gene_acc', 'genes'),
                       'ac': ('aid', 'assoc_id', 'associated_ids')}[centric]
        psm_sql = ('SELECT {0}.{1}, pp.psm_id, ps.sequence '
                   'FROM {2} AS {0} '
                   'JOIN protein_psm AS pp USING(protein_acc) '
                   'JOIN psms USING(psm_id) '
                   'JOIN peptide_sequences AS ps USING(pep_id) '
                   )
        psm_sql = psm_sql.format(*psm_sql_map)
        expected = {rec[0]: rec[1:] for rec in
                    self.get_values_from_db(self.dbfile, sql)}
        for protein in self.tsv_generator(self.resultfn):
            pacc = protein['Protein accession']
            self.assertEqual(protein['Gene'], expected[pacc][0])
            self.assertEqual(protein['Associated gene ID'], expected[pacc][1])
            self.assertEqual(protein['Description'], expected[pacc][2])
            self.assertEqual(protein['Coverage'], str(expected[pacc][3]))

        expected, unipeps = {}, {}
        for rec in self.get_values_from_db(self.dbfile, psm_sql):
            pacc = rec[0]
            try:
                unipeps[rec[2]].add(pacc)
            except KeyError:
                unipeps[rec[2]] = set([pacc])
            try:
                expected[pacc]['psms'].add(rec[1])
            except KeyError:
                expected[pacc] = {'psms': set([rec[1]]), 'pep': set([rec[2]]),
                                  'unipep': 0}
            else:
                expected[pacc]['pep'].add(rec[2])
        for pep, prot in unipeps.items():
            if len(prot) == 1:
                expected[prot.pop()]['unipep'] += 1
        for protein in self.tsv_generator(self.resultfn):
            pacc = protein['Protein accession']
            poolname = 'S1'
            self.assertEqual(protein['{}_# Unique peptides'.format(poolname)],
                             str(expected[pacc]['unipep']))
            self.assertEqual(protein['{}_# Peptides'.format(poolname)],
                             str(len(expected[pacc]['pep'])))
            self.assertEqual(protein['{}_# PSMs'.format(poolname)],
                             str(len(expected[pacc]['psms'])))