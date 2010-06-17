import MDAnalysis as mda

import numpy as np
from numpy.testing import *

from MDAnalysis.tests.datafiles import PSF,DCD,DCD_empty,PDB_small,PDB,XTC,TRR

class TestPDBReader(TestCase):
    def setUp(self):
        self.universe = mda.Universe(PDB_small)        

    def test_load_pdb(self):
        U = self.universe
        assert_equal(len(U.atoms), 3341, "load Universe from small PDB")
        assert_equal(U.atoms.selectAtoms('resid 150 and name HA2').atoms[0], 
                     U.atoms[2314], "Atom selections")

    def test_numatoms(self):
        assert_equal(self.universe.trajectory.numatoms, 3341, "wrong number of atoms")

    def test_numframes(self):
        assert_equal(self.universe.trajectory.numframes, 1, "wrong number of frames in pdb")


class TestPDBReaderBig(TestCase):
    @dec.slow
    def test_load_pdb(self):
        U = mda.Universe(PDB)
        assert_equal(len(U.atoms), 47681, "load Universe from big PDB")
        assert_equal(U.atoms.selectAtoms('resid 150 and name HA2').atoms[0], 
                     U.atoms[2314], "Atom selections")
        na = U.selectAtoms('resname NA+')
        assert_equal(len(na), 4, "Atom selection of last atoms in file")


def TestDCD_Issue32():
    """Issue 32: 0-size dcds lead to a sgefault: now caught with IOError"""
    assert_raises(IOError, mda.Universe, PSF, DCD_empty)

class _TestDCD(TestCase):
    def setUp(self):
        self.universe = mda.Universe(PSF, DCD)
        self.dcd = self.universe.trajectory
        self.ts = self.universe.coord

class TestDCDReader(_TestDCD):
    def test_rewind_dcd(self):
        self.dcd.rewind()
        assert_equal(self.ts.frame, 1, "rewinding to frame 1")

    def test_next_dcd(self):
        self.dcd.rewind()
        self.dcd.next()
        assert_equal(self.ts.frame, 2, "loading frame 2")

    def test_jump_dcd(self):
        self.dcd[15]  # index is 0-based but frames are 1-based
        assert_equal(self.ts.frame, 16, "jumping to frame 16")

    def test_numatoms(self):
        assert_equal(self.universe.trajectory.numatoms, 3341, "wrong number of atoms")

    def test_numframes(self):
        assert_equal(self.universe.trajectory.numframes, 98, "wrong number of frames in dcd")
        
class TestDCDCorrel(_TestDCD):
    def setUp(self):
        # Note: setUp is executed for *every* test !
        super(TestDCDCorrel, self).setUp()
        import MDAnalysis.core.Timeseries as TS
        self.collection = TS.TimeseriesCollection()
        C = self.collection
        all = self.universe.atoms
        ca = self.universe.s4AKE.CA
        ca_termini =  mda.core.AtomGroup.AtomGroup([ca[0], ca[-1]])
        phi151 = self.universe.selectAtoms('resid 151').selectAtoms('name HN', 'name N', 'name CA', 'name CB')
        C.addTimeseries(TS.Atom('v', ca_termini))       # 0
        C.addTimeseries(TS.Bond(ca_termini))            # 1
        C.addTimeseries(TS.Bond([ca[0], ca[-1]]))       # 2
        C.addTimeseries(TS.Angle(phi151[1:4]))          # 3
        C.addTimeseries(TS.Dihedral(phi151))            # 4
        C.addTimeseries(TS.Distance('r', ca_termini))   # 5
        C.addTimeseries(TS.CenterOfMass(ca))            # 6
        C.addTimeseries(TS.CenterOfGeometry(ca))        # 7
        C.addTimeseries(TS.CenterOfMass(all))           # 8
        C.addTimeseries(TS.CenterOfGeometry(all))       # 9
        # cannot test WaterDipole because there's no water in the test dcd
        C.compute(self.dcd)

    def test_correl(self):
        assert_equal(len(self.collection), 10, "Correl: len(collection)")

    def test_Atom(self):
        assert_equal(self.collection[0].shape, (2, 3, 98), 
                     "Correl: Atom positions")

    def test_Bonds(self):
        C = self.collection
        assert_array_equal(C[1].__data__, C[2].__data__, 
                           "Correl: Bonds with lists and AtomGroup")

    def test_Angle(self):
        C = self.collection
        avg_angle = 1.9111695972912988
        assert_almost_equal(C[3].__data__.mean(), avg_angle,
                            err_msg="Correl: average Angle")
        
    def test_Dihedral(self):
        C = self.collection
        avg_phi151 = 0.0088003870749735619        
        assert_almost_equal(C[4].__data__.mean(), avg_phi151,
                            err_msg="Correl: average Dihedral")

    def test_scalarDistance(self):
        C = self.collection        
        avg_dist = 9.7960210987736236
        assert_almost_equal(C[5].__data__.mean(), avg_dist,
                            err_msg="Correl: average scalar Distance")

    def test_CenterOfMass(self):
        C = self.collection
        avg_com_ca  = np.array([ 0.0043688 , -0.27812258, 0.0284051])
        avg_com_all = np.array([-0.10086529, -0.16357276, 0.12724672])
        assert_array_almost_equal(C[6].__data__.mean(axis=1), avg_com_ca,
                                  err_msg="Correl: average CA CenterOfMass")
        assert_almost_equal(C[8].__data__.mean(axis=1), avg_com_all,
                            err_msg="Correl: average all CenterOfMass")

    def test_CenterOfGeometry(self):
        C = self.collection        
        avg_cog_all = np.array([-0.13554797, -0.20521885, 0.2118998])
        assert_almost_equal(C[9].__data__.mean(axis=1), avg_cog_all,
                            err_msg="Correl: average all CenterOfGeometry")

    def test_CA_COMeqCOG(self):
        C = self.collection
        assert_array_almost_equal(C[6].__data__, C[7].__data__,
                                  err_msg="Correl: CA CentreOfMass == CenterOfGeometry")

    def test_clear(self):
        C = self.collection
        C.clear()
        assert_equal(len(C), 0, "Correl: clear()")
   
# notes:
def compute_correl_references():
    universe = MDAnalysis.Universe(PSF,DCD)

    all = universe.atoms
    ca = universe.s4AKE.CA
    ca_termini =  mda.core.AtomGroup.AtomGroup([ca[0], ca[-1]])
    phi151 = universe.selectAtoms('resid 151').selectAtoms('name HN', 'name N', 'name CA', 'name CB')

    C = MDAnalysis.collection
    C.clear()

    C.addTimeseries(TS.Atom('v', ca_termini))       # 0
    C.addTimeseries(TS.Bond(ca_termini))            # 1
    C.addTimeseries(TS.Bond([ca[0], ca[-1]]))       # 2
    C.addTimeseries(TS.Angle(phi151[1:4]))          # 3
    C.addTimeseries(TS.Dihedral(phi151))            # 4
    C.addTimeseries(TS.Distance('r', ca_termini))   # 5
    C.addTimeseries(TS.CenterOfMass(ca))            # 6
    C.addTimeseries(TS.CenterOfGeometry(ca))        # 7
    C.addTimeseries(TS.CenterOfMass(all))           # 8
    C.addTimeseries(TS.CenterOfGeometry(all))       # 9

    C.compute(universe.dcd)

    results = {"avg_angle": C[3].__data__.mean(),
               "avg_phi151": C[4].__data__.mean(),
               "avg_dist": C[5].__data__.mean(),
               "avg_com_ca": C[6].__data__.mean(axis=1), 
               "avg_com_all": C[8].__data__.mean(axis=1),
               "avg_cog_all": C[9].__data__.mean(axis=1),
               }
    C.clear()
    return results


class _GromacsReader(TestCase):
    filename = None
    def setUp(self):
        self.universe = mda.Universe(PDB, self.filename)
        self.trajectory = self.universe.trajectory
        self.ts = self.universe.coord
    
    @dec.slow
    def test_rewind_xdrtrj(self):
        self.trajectory.rewind()
        assert_equal(self.ts.frame, 1, "rewinding to frame 1")

    @dec.slow
    def test_next_xdrtrj(self):
        self.trajectory.rewind()
        self.trajectory.next()
        assert_equal(self.ts.frame, 2, "loading frame 2")

    @dec.slow
    def test_coordinates(self):
        # note: these are the native coordinates in nm; for the test to succeed:
        assert_equal(mda.core.flags['convert_gromacs_lengths'], True, 
                     "oops, mda.core.flags['convert_gromacs_lengths'] should be True")
        ca_nm = np.array([[ 6.043369675,  7.385184479,  1.381425762]], dtype=np.float32)
        # coordinates in the base unit (needed for True)
        ca_Angstrom = ca_nm * 10.0
        U = self.universe
        T = U.trajectory
        T.rewind()
        T.next()
        T.next()
        assert_equal(self.ts.frame, 3, "failed to step to frame 3")
        ca = U.selectAtoms('name CA and resid 122')
        # low precision match (2 decimals in A, 3 in nm) because the above are the trr coords
        assert_array_almost_equal(ca.coordinates(), ca_Angstrom, 2,
                                  err_msg="coords of Ca of resid 122 do not match for frame 3")

class TestXTCReader(_GromacsReader):
    filename = XTC

class TestTRRReader(_GromacsReader):
    filename = TRR


class _XDRNoConversion(TestCase):
    filename = None
    def setUp(self):
        mda.core.flags['convert_gromacs_lengths'] = False
        self.universe = mda.Universe(PDB, self.filename)
        self.ts = self.universe.trajectory.ts
    def tearDown(self):
        mda.core.flags['convert_gromacs_lengths'] = True  # default

    @dec.slow
    def test_coordinates(self):
        # note: these are the native coordinates in nm; for the test to succeed:
        assert_equal(mda.core.flags['convert_gromacs_lengths'], False, 
                     "oops, mda.core.flags['convert_gromacs_lengths'] should be False for this test")
        ca_nm = np.array([[ 6.043369675,  7.385184479,  1.381425762]], dtype=np.float32)
        U = self.universe
        T = U.trajectory
        T.rewind()
        T.next()
        T.next()
        assert_equal(self.ts.frame, 3, "failed to step to frame 3")        
        ca = U.selectAtoms('name CA and resid 122')
        # low precision match because we also look at the trr: only 3 decimals in nm in xtc!
        assert_array_almost_equal(ca.coordinates(), ca_nm, 3,
                                  err_msg="native coords of Ca of resid 122 do not match for frame 3 "\
                                      "with core.flags['convert_gromacs_lengths'] = False")

class TestXTCNoConversion(_XDRNoConversion):
    filename = XTC

class TestTRRNoConversion(_XDRNoConversion):
    filename = TRR
