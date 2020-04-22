"""Primary pipeline object for DANCE.

Provides a pipeline for generating molecule datasets from a database in various
formats.
"""
import glob
import pathlib
from typing import Union
from openeye import oechem


class DancePipeline:
    """A pipeline for creating diverse molecule datasets.

    The molecules are sourced from a database. Several types of databases may be
    used. ``database_type`` indicates the database type, and ``database_info``
    contains info for accessing the database. The following table lists the
    possible values for ``database_type``, and the corresponding info that must
    be provided in ``database_info``.

    +---------------+------------------------------------------------+-----------------------------+
    | database_type | database_info                                  | type                        |
    +===============+================================================+=============================+
    | SMILES        | The name of a file listing SMILES strings.     | ``str`` or ``pathlib.Path`` |
    +---------------+------------------------------------------------+-----------------------------+
    | MOL2_DIR      | The name of a directory containing mol2 files. | ``str`` or ``pathlib.Path`` |
    +---------------+------------------------------------------------+-----------------------------+

    .. note::
        The pipeline does not load any molecules when initialized, so
        initializing a pipeline is very cheap.

    Parameters
    ----------
    database_type : str
        The type of database.
    database_info : Union[str, pathlib.Path]
        Info for the database -- refer to above table for acceptable types.

    Attributes
    ----------
    database_type : str
        The type of database.
    database_info : Union[str, pathlib.Path]
        Info for the database -- refer to the above table for acceptable types.
    filter_output_oeb : pathlib.Path
        Output OEB (Openeye Binary) filename for the :meth:`~filter` step.
    fingerprint_output_csv : pathlib.Path
        Output CSV filename for the :meth:`~assign_fingerprint` step.
    SUPPORTED_DATABASE_TYPES : FrozenSet[str]
        Set of database types supported by the pipeline.
    """

    SUPPORTED_DATABASE_TYPES = frozenset(["SMILES", "MOL2_DIR"])

    def __init__(self, database_type: str, database_info):
        if database_type not in self.SUPPORTED_DATABASE_TYPES:
            raise RuntimeError(f"`{database_type}` is not a supported database type")

        self.database_type = database_type
        self.database_info = database_info
        self.filter_output_oeb = None
        self.fingerprint_output_csv = None

    def filter(self, relevance_function, output_oeb: Union[str, pathlib.Path] = "filter_output.oeb"):
        """Uses the ``relevance_function`` to choose molecules from the database.

        Each molecule from the database is read into an OEMol, and the
        ``relevance_function`` is used to determine whether the molecule is
        relevant or not. If the molecule is relevant, it is saved to the
        ``output_oeb`` file.

        ``output_oeb`` is stored in the ``filter_output_oeb`` attribute as a
        ``pathlib.Path`` for future reference by the pipeline.

        Parameters
        ----------
        relevance_function : function(molecule) -> bool
            A function which takes in a single OEMol and outputs a bool telling
            whether or not the molecule is relevant
        output_oeb : Union[str, pathlib.Path], optional
            Name of an OEB (Openeye Binary) file for storing the relevant
            molecules. If this file already exists, it will be overwritten!
        """
        self.filter_output_oeb = pathlib.Path(output_oeb)

        filtered_molecule_stream = oechem.oemolostream(str(output_oeb))
        for mol in self._generate_molecules_from_database():
            if relevance_function(mol):
                oechem.OEWriteMolecule(filtered_molecule_stream, mol)
        filtered_molecule_stream.close()

    def _generate_molecules_from_database(self) -> oechem.OEMol:
        """Generator which yields molecules from the database.

        Information about the database is passed in via the ``database_type``
        and ``database_info`` attributes of this class.
        """
        if self.database_type == "SMILES":
            ifs = oechem.oemolistream(str(self.database_info))
            for mol in ifs.GetOEMols():
                yield mol
        elif self.database_type == "MOL2_DIR":
            for mol2file in glob.iglob(str(pathlib.Path(self.database_info) / "*.mol2")):
                ifs = oechem.oemolistream(mol2file)
                mol = oechem.OEMol()
                oechem.OEReadMolecule(ifs, mol)
                yield mol