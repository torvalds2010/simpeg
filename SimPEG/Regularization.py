from __future__ import print_function

import numpy as np
import scipy.sparse as sp
import warnings
import properties

from . import Utils
from . import Maps
from . import Mesh
from . import ObjectiveFunction
from . import Props

__all__ = [
    'Smallness',
    'Smooth_x', 'Smooth_y', 'Smooth_z',
    'Smooth_xx', 'Smooth_yy', 'Smooth_zz',
    'SimpleSmooth_x', 'SimpleSmooth_y', 'SimpleSmooth_z',
    'Simple', 'Tikhonov',
    'SparseSmallness', 'Sparse_x', 'Sparse_y', 'Sparse_z', 'Sparse'
]


###############################################################################
#                                                                             #
#                             Regularization Mesh                             #
#                                                                             #
###############################################################################

class RegularizationMesh(Props.BaseSimPEG):
    """
    **Regularization Mesh**

    This contains the operators used in the regularization. Note that these
    are not necessarily true differential operators, but are constructed from
    a SimPEG Mesh.

    :param BaseMesh mesh: problem mesh
    :param numpy.array indActive: bool array, size nC, that is True where we have active cells. Used to reduce the operators so we regularize only on active cells

    """

    def __init__(self, mesh, **kwargs):
        self.mesh = mesh
        Utils.setKwargs(self, **kwargs)

    indActive = properties.Array("active indices in mesh", dtype=[bool, int])

    @properties.validator('indActive')
    def _cast_to_bool(self, change):
        value = change['value']
        if value is not None:
            if value.dtype != 'bool':  # cast it to a bool otherwise
                tmp = value
                value = np.zeros(self.mesh.nC, dtype=bool)
                value[tmp] = True
                change['value'] = value

    @property
    def vol(self):
        """
        reduced volume vector

        :rtype: numpy.array
        :return: reduced cell volume
        """
        if getattr(self, '_vol', None) is None:
            self._vol = self.Pac.T * self.mesh.vol
        return self._vol

    @property
    def nC(self):
        """
        reduced number of cells

        :rtype: int
        :return: number of cells being regularized
        """
        if self.indActive is not None:
            return int(self.indActive.sum())
        return self.mesh.nC


    @property
    def dim(self):
        """
        dimension of regularization mesh (1D, 2D, 3D)

        :rtype: int
        :return: dimension
        """
        if getattr(self, '_dim', None) is None:
            self._dim = self.mesh.dim
        return self._dim


    @property
    def Pac(self):
        """
        projection matrix that takes from the reduced space of active cells to
        full modelling space (ie. nC x nindActive)

        :rtype: scipy.sparse.csr_matrix
        :return: active cell projection matrix
        """
        if getattr(self, '_Pac', None) is None:
            if self.indActive is None:
                self._Pac = Utils.speye(self.mesh.nC)
            else:
                self._Pac = Utils.speye(self.mesh.nC)[:, self.indActive]
        return self._Pac

    @property
    def Pafx(self):
        """
        projection matrix that takes from the reduced space of active x-faces
        to full modelling space (ie. nFx x nindActive_Fx )

        :rtype: scipy.sparse.csr_matrix
        :return: active face-x projection matrix
        """
        if getattr(self, '_Pafx', None) is None:
            if self.indActive is None:
                self._Pafx = Utils.speye(self.mesh.nFx)
            else:
                indActive_Fx = (self.mesh.aveFx2CC.T * self.indActive) == 1
                self._Pafx = Utils.speye(self.mesh.nFx)[:, indActive_Fx]
        return self._Pafx

    @property
    def Pafy(self):
        """
        projection matrix that takes from the reduced space of active y-faces
        to full modelling space (ie. nFy x nindActive_Fy )

        :rtype: scipy.sparse.csr_matrix
        :return: active face-y projection matrix
        """
        if getattr(self, '_Pafy', None) is None:
            if self.indActive is None:
                self._Pafy = Utils.speye(self.mesh.nFy)
            else:
                indActive_Fy = (self.mesh.aveFy2CC.T * self.indActive) == 1
                self._Pafy = Utils.speye(self.mesh.nFy)[:, indActive_Fy]
        return self._Pafy

    @property
    def Pafz(self):
        """
        projection matrix that takes from the reduced space of active z-faces
        to full modelling space (ie. nFz x nindActive_Fz )

        :rtype: scipy.sparse.csr_matrix
        :return: active face-z projection matrix
        """
        if getattr(self, '_Pafz', None) is None:
            if self.indActive is None:
                self._Pafz = Utils.speye(self.mesh.nFz)
            else:
                indActive_Fz = (self.mesh.aveFz2CC.T * self.indActive) == 1
                self._Pafz = Utils.speye(self.mesh.nFz)[:, indActive_Fz]
        return self._Pafz

    @property
    def aveFx2CC(self):
        """
        averaging from active cell centers to active x-faces

        :rtype: scipy.sparse.csr_matrix
        :return: averaging from active cell centers to active x-faces
        """
        if getattr(self, '_aveFx2CC', None) is None:
            self._aveFx2CC = self.Pac.T * self.mesh.aveFx2CC * self.Pafx
        return self._aveFx2CC

    @property
    def aveCC2Fx(self):
        """
        averaging from active x-faces to active cell centers

        :rtype: scipy.sparse.csr_matrix
        :return: averaging matrix from active x-faces to active cell centers
        """
        if getattr(self, '_aveCC2Fx', None) is None:
            self._aveCC2Fx = (
                Utils.sdiag(1./(self.aveFx2CC.T).sum(1)) * self.aveFx2CC.T
            )
        return self._aveCC2Fx

    @property
    def aveFy2CC(self):
        """
        averaging from active cell centers to active y-faces

        :rtype: scipy.sparse.csr_matrix
        :return: averaging from active cell centers to active y-faces
        """
        if getattr(self, '_aveFy2CC', None) is None:
            self._aveFy2CC = self.Pac.T * self.mesh.aveFy2CC * self.Pafy
        return self._aveFy2CC

    @property
    def aveCC2Fy(self):
        """
        averaging from active y-faces to active cell centers

        :rtype: scipy.sparse.csr_matrix
        :return: averaging matrix from active y-faces to active cell centers
        """
        if getattr(self, '_aveCC2Fy', None) is None:
            self._aveCC2Fy = (
                Utils.sdiag(1./(self.aveFy2CC.T).sum(1)) * self.aveFy2CC.T
            )
        return self._aveCC2Fy

    @property
    def aveFz2CC(self):
        """
        averaging from active cell centers to active z-faces

        :rtype: scipy.sparse.csr_matrix
        :return: averaging from active cell centers to active z-faces
        """
        if getattr(self, '_aveFz2CC', None) is None:
            self._aveFz2CC = self.Pac.T * self.mesh.aveFz2CC * self.Pafz
        return self._aveFz2CC

    @property
    def aveCC2Fz(self):
        """
        averaging from active z-faces to active cell centers

        :rtype: scipy.sparse.csr_matrix
        :return: averaging matrix from active z-faces to active cell centers
        """
        if getattr(self, '_aveCC2Fz', None) is None:
            self._aveCC2Fz = (
                Utils.sdiag(1./(self.aveFz2CC.T).sum(1)) * self.aveFz2CC.T
            )
        return self._aveCC2Fz

    @property
    def cellDiffx(self):
        """
        cell centered difference in the x-direction

        :rtype: scipy.sparse.csr_matrix
        :return: differencing matrix for active cells in the x-direction
        """
        if getattr(self, '_cellDiffx', None) is None:
            self._cellDiffx = self.Pafx.T * self.mesh.cellGradx * self.Pac
        return self._cellDiffx

    @property
    def cellDiffy(self):
        """
        cell centered difference in the y-direction

        :rtype: scipy.sparse.csr_matrix
        :return: differencing matrix for active cells in the y-direction
        """
        if getattr(self, '_cellDiffy', None) is None:
            self._cellDiffy = self.Pafy.T * self.mesh.cellGrady * self.Pac
        return self._cellDiffy

    @property
    def cellDiffz(self):
        """
        cell centered difference in the z-direction

        :rtype: scipy.sparse.csr_matrix
        :return: differencing matrix for active cells in the z-direction
        """
        if getattr(self, '_cellDiffz', None) is None:
            self._cellDiffz = self.Pafz.T * self.mesh.cellGradz * self.Pac
        return self._cellDiffz

    @property
    def faceDiffx(self):
        """
        x-face differences

        :rtype: scipy.sparse.csr_matrix
        :return: differencing matrix for active faces in the x-direction
        """
        if getattr(self, '_faceDiffx', None) is None:
            self._faceDiffx = self.Pac.T * self.mesh.faceDivx * self.Pafx
        return self._faceDiffx

    @property
    def faceDiffy(self):
        """
        y-face differences

        :rtype: scipy.sparse.csr_matrix
        :return: differencing matrix for active faces in the y-direction
        """
        if getattr(self, '_faceDiffy', None) is None:
            self._faceDiffy = self.Pac.T * self.mesh.faceDivy * self.Pafy
        return self._faceDiffy

    @property
    def faceDiffz(self):
        """
        z-face differences

        :rtype: scipy.sparse.csr_matrix
        :return: differencing matrix for active faces in the z-direction
        """
        if getattr(self, '_faceDiffz', None) is None:
            self._faceDiffz = self.Pac.T * self.mesh.faceDivz * self.Pafz
        return self._faceDiffz

    @property
    def cellDiffxStencil(self):
        """
        cell centered difference stencil (no cell lengths include) in the
        x-direction

        :rtype: scipy.sparse.csr_matrix
        :return: differencing matrix for active cells in the x-direction
        """
        if getattr(self, '_cellDiffxStencil', None) is None:

            self._cellDiffxStencil = (
                self.Pafx.T * self.mesh._cellGradxStencil() * self.Pac
            )
        return self._cellDiffxStencil

    @property
    def cellDiffyStencil(self):
        """
        cell centered difference stencil (no cell lengths include) in the
        y-direction

        :rtype: scipy.sparse.csr_matrix
        :return: differencing matrix for active cells in the y-direction
        """
        if self.dim < 2:
            return None
        if getattr(self, '_cellDiffyStencil', None) is None:

            self._cellDiffyStencil = (
                self.Pafy.T * self.mesh._cellGradyStencil() * self.Pac
            )
        return self._cellDiffyStencil

    @property
    def cellDiffzStencil(self):
        """
        cell centered difference stencil (no cell lengths include) in the
        y-direction

        :rtype: scipy.sparse.csr_matrix
        :return: differencing matrix for active cells in the y-direction
        """
        if self.dim < 3:
            return None
        if getattr(self, '_cellDiffzStencil', None) is None:

            self._cellDiffzStencil = (
                self.Pafz.T * self.mesh._cellGradzStencil() * self.Pac
            )
        return self._cellDiffzStencil


###############################################################################
#                                                                             #
#                          Single Regularization                              #
#                                                                             #
###############################################################################

class BaseRegularization(ObjectiveFunction.BaseObjectiveFunction):
    """
    Base class for regularization. Inherit this for building your own
    regularization. The base regularization assumes a weighted l2 style of
    regularization. However, if you wish to employ a different norm, the
    methods :meth:`_eval`, :meth:`deriv` and :meth:`deriv2` can be over-written

    **Optional Inputs**

    :param BaseMesh mesh: SimPEG mesh
    :param int nP: number of parameters
    :param IdentityMap mapping: regularization mapping, takes the model from model space to the space you want to regularize in
    :param numpy.ndarray mref: reference model
    :param numpy.ndarray indActive: active cell indices for reducing the size
    of differential operators in the definition of a regularization mesh

    """

    counter = None

    def __init__(
        self, mesh=None, **kwargs
    ):

        super(BaseRegularization, self).__init__()
        self._mesh = mesh
        Utils.setKwargs(self, **kwargs)

    # Properties
    mref = Props.Array(
        "reference model", default=Utils.Zero()
    )
    indActive = properties.Array(
        "indices of active cells in the mesh", dtype=(bool, int)
    )
    cell_weights = properties.Array(
        "regularization weights applied at cell centers", dtype=float
    )

    # Observers and Validators
    @properties.validator('indActive')
    def _cast_to_bool(self, change):
        value = change['value']
        if value is not None:
            if value.dtype != 'bool':  # cast it to a bool otherwise
                tmp = value
                value = np.zeros(self.mesh.nC, dtype=bool)
                value[tmp] = True
                change['value'] = value

        # update regmesh indActive
        if getattr(self, 'regmesh', None) is not None:
            self.regmesh.indActive = Utils.mkvc(value)

    @properties.observer('indActive')
    def _update_regmesh_indActive(self, change):
        # update regmesh indActive
        if getattr(self, 'regmesh', None) is not None:
            self.regmesh.indActive = change['value']

    @properties.validator('mref')
    def _validate_mref(self, change):
        if not isinstance(change['value'], Utils.Zero) and self.nP != '*':
            assert len(change['value']) == self.nP, (
                'mref must be length {}'.format(self.nP)
            )

    @properties.validator('cell_weights')
    def _validate_cell_weights(self, change):
        if change['value'] is not None and self.nP != '*':
            assert len(change['value']) == self.nP, (
                'cell_weights must be length {} not {}'.format(
                    self.nP, len(change['value'])
                )
            )

    # Other properties and methods
    @property
    def nP(self):
        """
        number of model parameters
        """
        if getattr(self.mapping, 'nP') != '*':
            return self.mapping.nP
        elif getattr(self.regmesh, 'nC') != '*':
            return self.regmesh.nC
        else:
            return '*'

    @property
    def mesh(self):
        """
        a SimPEG mesh which the model is described on
        """
        return self._mesh

    @mesh.setter
    def mesh(self, value):
        assert isinstance(value, Mesh.BaseMesh) or value is None, (
            "mesh must be a SimPEG.Mesh object."
        )
        self._mesh = value

    @property
    def regmesh(self):
        """
        mesh used for creating operators for regularization. Excludes inactive
        cells if they are provided
        """
        if getattr(self, '_regmesh', None) is None:
            if self.indActive is not None:
                self._regmesh = RegularizationMesh(
                    self.mesh, indActive=self.indActive
                )
            else:
                self._regmesh = RegularizationMesh(self.mesh)
        return self._regmesh

    @regmesh.setter
    def regmesh(self, value):
        assert isinstance(value, RegularizationMesh) or value is None, (
            "regmesh must be an instance of a RegularizationMesh"
            )
        self._regmesh = value

    @property
    def mapping(self):
        """
        a mapping to map the model to the space in which you wish to regularize
        it in
        """
        if getattr(self, '_mapping', None) is None:
            return self.mapPair()
        return self._mapping

    @mapping.setter
    def mapping(self, value):
        if value is not None:
            value._assertMatchesPair(self.mapPair)
        self._mapping = value


    @Utils.timeIt
    def _eval(self, m):
        """
        We use a weighted 2-norm objective function

        .. math::

            r(m) = \\frac{1}{2}
        """
        r = self.W * (self.mapping * (m - self.mref))
        return 0.5 * r.dot(r)

    @Utils.timeIt
    def deriv(self, m):
        """

        The regularization is:

        .. math::

            R(m) = \\frac{1}{2}\mathbf{(m-m_\\text{ref})^\\top W^\\top
                   W(m-m_\\text{ref})}

        So the derivative is straight forward:

        .. math::

            R(m) = \mathbf{W^\\top W (m-m_\\text{ref})}

        """

        mD = self.mapping.deriv(m - self.mref)
        r = self.W * (self.mapping * (m - self.mref))
        return mD.T * (self.W.T * r)

    @Utils.timeIt
    def deriv2(self, m, v=None):
        """
        Second derivative

        :param numpy.array m: geophysical model
        :param numpy.array v: vector to multiply
        :rtype: scipy.sparse.csr_matrix
        :return: WtW, or if v is supplied WtW*v (numpy.ndarray)

        The regularization is:

        .. math::

            R(m) = \\frac{1}{2}\mathbf{(m-m_\\text{ref})^\\top W^\\top
            W(m-m_\\text{ref})}

        So the second derivative is straight forward:

        .. math::

            R(m) = \mathbf{W^\\top W}

        """
        mD = self.mapping.deriv(m - self.mref)
        if v is None:
            return mD.T * self.W.T * self.W * mD

        return mD.T * ( self.W.T * ( self.W * ( mD * v) ) )


class Smallness(BaseRegularization):
    """
    Smallness regularization - L2 regularization on the difference between a
    model and a reference model. Cell weights may be included.

    .. math::

        r(m) = \\frac{1}{2}(\mathbf{m} - \mathbf{m_ref})^\top \mathbf{W}^T
        \mathbf{W} (\mathbf{m} - \mathbf{m_{ref}})

    where :math:`\mathbf{m}` is the model, :math:`\mathbf{m_{ref}}` is a
    reference model (default Zero) and :math:`\mathbf{W}` is a weighting
    matrix (default Identity. If cell weights are provided, then it is
    :code:`diag(cell_weights)`)

    **Optional Inputs**

    :param BaseMesh mesh: SimPEG mesh
    :param int nP: number of parameters
    :param IdentityMap mapping: regularization mapping, takes the model from model space to the space you want to regularize in
    :param numpy.ndarray mref: reference model
    :param numpy.ndarray indActive: active cell indices for reducing the size
    of differential operators in the definition of a regularization mesh
    :param numpy.ndarray cell_weights: cell weights

    """

    _multiplier_pair = 'alpha_s'

    def __init__(self, mesh=None, **kwargs):

        super(Smallness, self).__init__(
            mesh=mesh, **kwargs
        )

    @property
    def W(self):
        if self.cell_weights is not None:
            return Utils.sdiag(self.cell_weights)
        else:
            return (
                sp.eye(self.nP) if self.nP != '*' else Utils.Identity()
            )


###############################################################################
#                                                                             #
#                           Combo Regularization                              #
#                                                                             #
###############################################################################

class BaseComboRegularization(ObjectiveFunction.ComboObjectiveFunction):

    mapPair = Maps.IdentityMap

    def __init__(
        self, mesh, objfcts=[],
        mapping=None, **kwargs
    ):

        # self._cell_weights = cell_weights
        self._mesh = mesh
        self._mapping = mapping
        # self.objfcts = objfcts

        super(BaseComboRegularization, self).__init__(
            objfcts=objfcts, multipliers=None
        )

        Utils.setKwargs(self, **kwargs)

    # Properties
    alpha_s = Props.Float("smallness weight")
    alpha_x = Props.Float("weight for the first x-derivative")
    alpha_y = Props.Float("weight for the first y-derivative")
    alpha_z = Props.Float("weight for the first z-derivative")
    alpha_xx = Props.Float("weight for the second x-derivative")
    alpha_yy = Props.Float("weight for the second y-derivative")
    alpha_zz = Props.Float("weight for the second z-derivative")

    mref = Props.Array(
        "reference model"
    )
    mrefInSmooth = properties.Bool(
        "include mref in the smoothness calculation?", default=False
    )
    indActive = properties.Array(
        "indices of active cells in the mesh", dtype=(bool, int)
    )
    cell_weights = properties.Array(
        "regularization weights applied at cell centers", dtype=float
    )

    @property
    def nP(self):
        if getattr(self.mapping, 'nP') != '*':
            return self.mapping.nP
        elif getattr(self.regmesh, 'nC') != '*':
            return self.regmesh.nC
        else:
            return '*'

    @property
    def multipliers(self):
        """
        Factors that multiply the objective functions that are summed together
        to build to composite regularization
        """
        return [
            getattr(
                self, '{alpha}'.format(alpha=objfct._multiplier_pair)
            ) for objfct in self.objfcts
        ]

    # Mirror property changes down to objective functions in objective function
    # list
    @properties.observer('mref')
    def _mirror_mref_to_objfctlist(self, change):
        for fct in self.objfcts:
            if getattr(fct, 'mrefInSmooth', None) is not None:
                if self.mrefInSmooth is False:
                    fct.mref = Utils.Zero()
                else:
                    fct.mref = change['value']
            else:
                fct.mref = change['value']

    @properties.observer('mrefInSmooth')
    def _mirror_mrefInSmooth_to_objfctlist(self, change):
        for fct in self.objfcts:
            if getattr(fct, 'mrefInSmooth', None) is not None:
                fct.mrefInSmooth = change['value']

    @properties.observer('indActive')
    def _mirror_indActive_to_objfctlist(self, change):
        value = change['value']
        if value is not None:
            if value.dtype != 'bool':
                tmp = value
                value = np.zeros(self.mesh.nC, dtype=bool)
                value[tmp] = True
                change['value'] = value

        if getattr(self, 'regmesh', None) is not None:
            self.regmesh.indActive = value

        for fct in self.objfcts:
            fct.indActive = value

    @properties.observer('cell_weights')
    def _mirror_cell_weights_to_objfctlist(self, change):
        for fct in self.objfcts:
            fct.cell_weights = change['value']

    # Mirror other properties down

    @property
    def mesh(self):
        """
        a SimPEG mesh which the model is described on
        """
        return self._mesh

    @mesh.setter
    def mesh(self, value):
        assert isinstance(value, Mesh.BaseMesh) or value is None, (
            "mesh must be a SimPEG.Mesh object."
        )
        for fct in self.objfcts:
            fct.mesh = value
        self._mesh = value

    @property
    def regmesh(self):
        # This could be cleaned up
        if getattr(self, 'mesh', None) is not None:
            if getattr(self, '_regmesh', None) is None:
                self._regmesh = RegularizationMesh(mesh=self.mesh)
                if self.indActive is not None:
                    self._regmesh.indActive = self.indActive
            return self._regmesh
        return None

    @regmesh.setter
    def regmesh(self, val):
        for fct in self.objfcts:
            fct.regmesh = val
        self._regmesh = val

    @property
    def mapping(self):
        if getattr(self, '_mapping', None) is None:
            if getattr(self, 'regmesh', None) is not None:
                self._mapping = self.mapPair()
            else:
                self._mapping = None
        return self._mapping

    @mapping.setter
    def mapping(self, val):
        for fct in self.objfcts:
            fct.mapping = val
        self._mapping = val


class BaseSimpleSmooth(BaseRegularization):
    """
    Base Simple Smooth Regularization. This base class regularizes on the first
    spatial derivative, not considering length scales, in the provided
    orientation

    **Optional Inputs**

    :param BaseMesh mesh: SimPEG mesh
    :param int nP: number of parameters
    :param IdentityMap mapping: regularization mapping, takes the model from model space to the space you want to regularize in
    :param numpy.ndarray mref: reference model
    :param numpy.ndarray indActive: active cell indices for reducing the size of differential operators in the definition of a regularization mesh
    :param numpy.ndarray cell_weights: cell weights
    :param bool mrefInSmooth: include the reference model in the smoothness computation? (eg. look at Deriv of m (False) or Deriv of (m-mref) (True))
    :param numpy.ndarray cell_weights: vector of cell weights (applied in all terms)
    """

    def __init__(
        self, mesh, orientation='x', **kwargs
    ):

        self.orientation = orientation
        assert self.orientation in ['x', 'y', 'z'], (
            "Orientation must be 'x', 'y' or 'z'"
        )

        super(BaseSimpleSmooth, self).__init__(
            mesh=mesh, **kwargs
        )

    mrefInSmooth = properties.Bool(
        "include mref in the smoothness calculation?", default=False
    )

    @property
    def W(self):
        """
        Weighting matrix that takes the first spatial difference (no
        length scales considered) in the specified orientation
        """
        W = getattr(
            self.regmesh,
            "cellDiff{orientation}Stencil".format(
                orientation=self.orientation
            )
        )
        if self.cell_weights is not None:
            Ave = getattr(self.regmesh, 'aveCC2F{}'.format(self.orientation))
            W = (
                Utils.sdiag(
                    (Ave*self.cell_weights)**0.5
                ) * W
            )
        return W


class SimpleSmooth_x(BaseSimpleSmooth):
    """
    Simple Smoothness along x. Regularizes on the first spatial derivative in
    the x-direction, not considering length scales
    """

    _multiplier_pair = 'alpha_x'

    def __init__(self, mesh, **kwargs):
        super(SimpleSmooth_x, self).__init__(
            mesh=mesh, orientation='x', **kwargs
        )


class SimpleSmooth_y(BaseSimpleSmooth):
    """
    Simple Smoothness along x. Regularizes on the first spatial derivative in
    the y-direction, not considering length scales
    """

    _multiplier_pair = 'alpha_y'

    def __init__(self, mesh, **kwargs):
        assert(mesh.dim > 1), (
            "Mesh must have at least 2 dimensions to regularize along the "
            "y-direction"
        )

        super(SimpleSmooth_y, self).__init__(
            mesh=mesh, orientation='y', **kwargs
        )


class SimpleSmooth_z(BaseSimpleSmooth):
    """
    Simple Smoothness along x. Regularizes on the first spatial derivative in
    the z-direction, not considering length scales
    """

    _multiplier_pair = 'alpha_z'

    def __init__(self, mesh, **kwargs):

        assert(mesh.dim > 2), (
            "Mesh must have at least 3 dimensions to regularize along the "
            "z-direction"
        )

        super(SimpleSmooth_z, self).__init__(
            mesh=mesh, orientation='z', **kwargs
        )


class Simple(BaseComboRegularization):

    """
    Simple regularization that does not include length scales in the
    derivatives.

    .. math::

        r(\mathbf{m}) = \\alpha_s \phi_s + \\alpha_x \phi_x +
        \\alpha_y \phi_y + \\alpha_z \phi_z

    where:

    - :math:`\phi_s` is a :class:`SimPEG.Regularization.Smallness` instance
    - :math:`\phi_x` is a :class:`SimPEG.Regularization.SimpleSmooth_x` instance
    - :math:`\phi_y` is a :class:`SimPEG.Regularization.SimpleSmooth_y` instance
    - :math:`\phi_z` is a :class:`SimPEG.Regularization.SimpleSmooth_z` instance


    **Required Inputs**

    :param BaseMesh mesh: a SimPEG mesh

    **Optional Inputs**

    :param IdentityMap mapping: regularization mapping, takes the model from model space to the space you want to regularize in
    :param numpy.ndarray mref: reference model
    :param numpy.ndarray indActive: active cell indices for reducing the size of differential operators in the definition of a regularization mesh
    :param numpy.ndarray cell_weights: cell weights
    :param bool mrefInSmooth: include the reference model in the smoothness computation? (eg. look at Deriv of m (False) or Deriv of (m-mref) (True))
    :param numpy.ndarray cell_weights: vector of cell weights (applied in all terms)

    **Weighting Parameters**

    :param float alpha_s: weighting on the smallness (default 1.)
    :param float alpha_x: weighting on the x-smoothness (default 1.)
    :param float alpha_y: weighting on the y-smoothness (default 1.)
    :param float alpha_z: weighting on the z-smoothness(default 1.)

    """

    def __init__(
        self, mesh,
        alpha_s=1.0, alpha_x=1.0, alpha_y=1.0,
        alpha_z=1.0, **kwargs
    ):

        objfcts = [
            Smallness(mesh=mesh, **kwargs),
            SimpleSmooth_x(
                mesh=mesh,
                **kwargs
            )
        ]

        if mesh.dim > 1:
            objfcts.append(
                SimpleSmooth_y(
                    mesh=mesh,
                    **kwargs
                )
            )

        if mesh.dim > 2:
            objfcts.append(
                SimpleSmooth_z(
                    mesh=mesh,
                    **kwargs
                )
            )

        super(Simple, self).__init__(
            mesh=mesh, objfcts=objfcts, alpha_s=alpha_s, alpha_x=alpha_x,
            alpha_y=alpha_y, alpha_z=alpha_z, **kwargs
        )

        # self.alpha_s = alpha_s
        # self.alpha_x = alpha_x
        # self.alpha_y = alpha_y
        # self.alpha_z = alpha_z


class BaseSmooth(BaseRegularization):
    """
    Base Smooth Regularization. This base class regularizes on the first
    spatial derivative in the provided orientation

    **Optional Inputs**

    :param BaseMesh mesh: SimPEG mesh
    :param int nP: number of parameters
    :param IdentityMap mapping: regularization mapping, takes the model from model space to the space you want to regularize in
    :param numpy.ndarray mref: reference model
    :param numpy.ndarray indActive: active cell indices for reducing the size of differential operators in the definition of a regularization mesh
    :param numpy.ndarray cell_weights: cell weights
    :param bool mrefInSmooth: include the reference model in the smoothness computation? (eg. look at Deriv of m (False) or Deriv of (m-mref) (True))
    :param numpy.ndarray cell_weights: vector of cell weights (applied in all terms)
    """

    mrefInSmooth = properties.Bool(
        "include mref in the smoothness calculation?", default=False
    )

    def __init__(
        self, mesh, orientation='x', **kwargs
    ):

        self.orientation = orientation

        assert orientation in ['x', 'y', 'z'], (
                "Orientation must be 'x', 'y' or 'z'"
            )

        super(BaseSmooth, self).__init__(
            mesh=mesh, **kwargs
        )

        if self.mrefInSmooth is False:
            self.mref = Utils.Zero()



    @property
    def W(self):
        """
        Weighting matrix that constructs the first spatial derivative stencil
        in the specified orientation
        """
        W = getattr(
            self.regmesh,
            "cellDiff{orientation}".format(
                orientation=self.orientation
            )
        )
        if self.cell_weights is not None:
            Ave = getattr(self.regmesh, 'aveCC2F{}'.format(self.orientation))
            W = (
                Utils.sdiag(
                    (Ave*self.cell_weights)**0.5
                ) * W
            )
        return W


class Smooth_x(BaseSmooth):
    """
    Smoothness along x. Regularizes on the first spatial derivative in the
    x-direction
    """

    _multiplier_pair = 'alpha_x'

    def __init__(self, mesh, **kwargs):
        super(Smooth_x, self).__init__(
            mesh=mesh, orientation='x', **kwargs
        )


class Smooth_y(BaseSmooth):
    """
    Smoothness along y. Regularizes on the first spatial derivative in the
    y-direction
    """

    _multiplier_pair = 'alpha_y'

    def __init__(self, mesh, **kwargs):
        assert(mesh.dim > 1), (
            "Mesh must have at least 2 dimensions to regularize along the "
            "y-direction"
        )

        super(Smooth_y, self).__init__(
            mesh=mesh, orientation='y', **kwargs
        )


class Smooth_z(BaseSmooth):
    """
    Smoothness along z. Regularizes on the first spatial derivative in the
    z-direction
    """

    _multiplier_pair = 'alpha_z'

    def __init__(self, mesh, **kwargs):
        assert(mesh.dim > 2), (
            "Mesh must have at least 3 dimensions to regularize along the "
            "z-direction"
        )

        super(Smooth_z, self).__init__(
            mesh=mesh, orientation='z', **kwargs
        )


class BaseSmooth2(BaseSmooth):
    """
    Base Smooth Regularization. This base class regularizes on the second
    spatial derivative in the provided orientation

    **Optional Inputs**

    :param BaseMesh mesh: SimPEG mesh
    :param int nP: number of parameters
    :param IdentityMap mapping: regularization mapping, takes the model from model space to the space you want to regularize in
    :param numpy.ndarray mref: reference model
    :param numpy.ndarray indActive: active cell indices for reducing the size of differential operators in the definition of a regularization mesh
    :param numpy.ndarray cell_weights: cell weights
    :param bool mrefInSmooth: include the reference model in the smoothness computation? (eg. look at Deriv of m (False) or Deriv of (m-mref) (True))
    :param numpy.ndarray cell_weights: vector of cell weights (applied in all terms)
    """

    def __init__(
        self, mesh,
        orientation='x',
        **kwargs
    ):
        self.orientation = orientation
        super(BaseSmooth2, self).__init__(
            mesh=mesh, **kwargs
        )


    @property
    def W(self):
        """
        Weighting matrix that takes the second spatial derivative in the
        specified orientation
        """
        vol = self.regmesh.vol
        if self.cell_weights is not None:
            vol *= self.cell_weights

        W = (
            Utils.sdiag(vol**0.5) *
            getattr(
                self.regmesh,
                'faceDiff{orientation}'.format(
                    orientation=self.orientation
                )
            ) *
            getattr(
                self.regmesh,
                'cellDiff{orientation}'.format(
                    orientation=self.orientation
                )
            )
        )
        return W


class Smooth_xx(BaseSmooth2):
    """
    Second-order smoothness along x. Regularizes on the second spatial
    derivative in the x-direction
    """

    _multiplier_pair = 'alpha_xx'

    def __init__(self, mesh, **kwargs):
        super(Smooth_xx, self).__init__(
            mesh=mesh, orientation='x', **kwargs
        )


class Smooth_yy(BaseSmooth2):
    """
    Second-order smoothness along y. Regularizes on the second spatial
    derivative in the y-direction
    """

    _multiplier_pair = 'alpha_yy'

    def __init__(self, mesh, **kwargs):
        assert(mesh.dim > 1), (
            "Mesh must have at least 2 dimensions to regularize along the "
            "y-direction"
        )
        super(Smooth_yy, self).__init__(
            mesh=mesh, orientation='y', **kwargs
        )


class Smooth_zz(BaseSmooth2):
    """
    Second-order smoothness along z. Regularizes on the second spatial
    derivative in the z-direction
    """

    _multiplier_pair = 'alpha_zz'

    def __init__(self, mesh, **kwargs):
        assert(mesh.dim > 2), (
            "Mesh must have at least 3 dimensions to regularize along the "
            "z-direction"
        )
        super(Smooth_zz, self).__init__(
            mesh=mesh, orientation='z', **kwargs
        )


class Tikhonov(BaseComboRegularization):
    """
    L2 Tikhonov regularization with both smallness and smoothness (first order
    derivative) contributions.

    .. math::
        \phi_m(\mathbf{m}) = \\alpha_s \| W_s (\mathbf{m} - \mathbf{m_{ref}} ) \|^2
        + \\alpha_x \| W_x \\frac{\partial}{\partial x} (\mathbf{m} - \mathbf{m_{ref}} ) \|^2
        + \\alpha_y \| W_y \\frac{\partial}{\partial y} (\mathbf{m} - \mathbf{m_{ref}} ) \|^2
        + \\alpha_z \| W_z \\frac{\partial}{\partial z} (\mathbf{m} - \mathbf{m_{ref}} ) \|^2

    Note if the key word argument `mrefInSmooth` is False, then mref is not
    included in the smoothness contribution.

    :param BaseMesh mesh: SimPEG mesh
    :param IdentityMap mapping: regularization mapping, takes the model from model space to the thing you want to regularize
    :param numpy.ndarray indActive: active cell indices for reducing the size of differential operators in the definition of a regularization mesh
    :param bool mrefInSmooth: (default = False) put mref in the smoothness component?
    :param float alpha_s: (default 1e-6) smallness weight
    :param float alpha_x: (default 1) smoothness weight for first derivative in the x-direction
    :param float alpha_y: (default 1) smoothness weight for first derivative in the y-direction
    :param float alpha_z: (default 1) smoothness weight for first derivative in the z-direction
    :param float alpha_xx: (default 1) smoothness weight for second derivative in the x-direction
    :param float alpha_yy: (default 1) smoothness weight for second derivative in the y-direction
    :param float alpha_zz: (default 1) smoothness weight for second derivative in the z-direction
    """

    def __init__(
        self, mesh,
        alpha_s=1e-6, alpha_x=1.0, alpha_y=1.0, alpha_z=1.0,
        alpha_xx=Utils.Zero(), alpha_yy=Utils.Zero(), alpha_zz=Utils.Zero(),
        **kwargs
    ):

        objfcts = [
            Smallness(mesh=mesh, **kwargs),
            Smooth_x(mesh=mesh, **kwargs),
            Smooth_xx(mesh=mesh, **kwargs)
        ]

        if mesh.dim > 1:
            objfcts += [
                    Smooth_y(mesh=mesh, **kwargs),
                    Smooth_yy(mesh=mesh, **kwargs)
            ]

        if mesh.dim > 2:
            objfcts += [
                    Smooth_z(mesh=mesh, **kwargs),
                    Smooth_zz(mesh=mesh, **kwargs)
            ]

        super(Tikhonov, self).__init__(
            mesh,
            alpha_s=alpha_s, alpha_x=alpha_x, alpha_y=alpha_y, alpha_z=alpha_z,
            alpha_xx=alpha_xx, alpha_yy=alpha_yy, alpha_zz=alpha_zz,
            objfcts=objfcts, **kwargs
        )


class BaseSparse(BaseRegularization):
    """
    Base class for building up the components of the Sparse Regularization
    """
    def __init__(self, mesh, **kwargs):
        super(BaseSparse, self).__init__(mesh=mesh, **kwargs)

    model = properties.Array(
        "current model", dtype=float
    )
    gamma = properties.Float(
        "Model norm scaling to smooth out convergence", default=1.
    )
    epsilon = properties.Float(
        "Threshold value for the model norm", default=1e-1
    )
    norm = properties.Float(
        "norm used", default=2
    )

    def R(self, f_m):
        # Eta scaling is important for mix-norms...do not mess with it
        eps = self.epsilon
        exponent = self.norm
        eta = (eps**(1.-exponent/2.))**0.5
        r = eta / (f_m**2. + eps**2.)**((1.-exponent/2.)/2.)

        return r


class SparseSmallness(BaseSparse):
    """
    Sparse smallness regularization

    **Inputs**

    :param int norm: norm on the smallness
    """

    _multiplier_pair = 'alpha_s'

    def __init__(self, mesh, norm=0, **kwargs):
        super(SparseSmallness, self).__init__(
            mesh=mesh, norm=norm, **kwargs
        )

    @property
    def W(self):
        if getattr(self, 'model', None) is None:
            R = Utils.speye(self.regmesh.nC)
        else:
            f_m = self.mapping * (self.model - self.mref)
            r = self.R(f_m) #, self.eps_p, self.norm)
            R = Utils.sdiag(r)

        if self.cell_weights is not None:
            return Utils.sdiag((self.gamma*self.cell_weights)**0.5) * R
        return (self.gamma)**0.5 * R


class BaseSparseDeriv(BaseSparse):
    """
    Base Class for sparse regularization on first spatial derivatives
    """

    def __init__(self, mesh, orientation='x', **kwargs):

        self.orientation = orientation
        super(BaseSparseDeriv, self).__init__(mesh=mesh, **kwargs)

    mrefInSmooth = properties.Bool(
        "include mref in the smoothness calculation?", default=False
    )

    @property
    def W(self):

        cellDiffStencil = getattr(
            self.regmesh, 'cellDiff{}Stencil'.format(self.orientation)
        )
        Ave = getattr(self.regmesh, 'aveCC2F{}'.format(self.orientation))

        if getattr(self, 'model', None) is None:
            R = Utils.speye(cellDiffStencil.shape[0])

        else:
            f_m = cellDiffStencil * (self.mapping * self.model)
            r = self.R(f_m) # , self.eps_q, self.norm)
            R = Utils.sdiag(r)

        if self.cell_weights is not None:
            return (
                Utils.sdiag(
                    (self.gamma*(Ave*self.cell_weights))**0.5
                ) *
                R * cellDiffStencil
            )
        return ( (self.gamma)**0.5) * R * cellDiffStencil


class Sparse_x(BaseSparseDeriv):
    """
    Regularization on the first derivative in the x-direction
    """

    _multiplier_pair = 'alpha_x'

    def __init__(self, mesh, **kwargs):

        super(Sparse_x, self).__init__(mesh=mesh, orientation='x', **kwargs)


class Sparse_y(BaseSparseDeriv):
    """
    Regularization on the first derivative in the y-direction
    """

    _multiplier_pair = 'alpha_y'

    def __init__(self, mesh, **kwargs):

        assert mesh.dim > 1, (
            "Mesh must have at least 2 dimensions to regularize along the "
            "y-direction"
        )

        super(Sparse_y, self).__init__(mesh=mesh, orientation='y', **kwargs)


class Sparse_z(BaseSparseDeriv):
    """
    Regularization on the first derivative in the z-direction
    """

    _multiplier_pair = 'alpha_z'

    def __init__(self, mesh, **kwargs):

        assert mesh.dim > 2, (
            "Mesh must have at least 3 dimensions to regularize along the "
            "z-direction"
        )

        super(Sparse_z, self).__init__(mesh=mesh, orientation='z', **kwargs)


class Sparse(BaseComboRegularization):
    """
    The regularization is:

    .. math::

        R(m) = \\frac{1}{2}\mathbf{(m-m_\\text{ref})^\\top W^\\top R^\\top R
        W(m-m_\\text{ref})}

    where the IRLS weight

    .. math::

        R = \eta TO FINISH LATER!!!

    So the derivative is straight forward:

    .. math::

        R(m) = \mathbf{W^\\top R^\\top R W (m-m_\\text{ref})}

    The IRLS weights are recomputed after each beta solves.
    It is strongly recommended to do a few Gauss-Newton iterations
    before updating.
    """
    def __init__(
        self, mesh,
        alpha_s=1.0, alpha_x=1.0, alpha_y=1.0, alpha_z=1.0,
        **kwargs
    ):

        objfcts = [
            SparseSmallness(mesh=mesh, **kwargs),
            Sparse_x(mesh=mesh, **kwargs)
        ]

        if mesh.dim > 1:
            objfcts.append(Sparse_y(mesh=mesh, **kwargs))

        if mesh.dim > 2:
            objfcts.append(Sparse_z(mesh=mesh, **kwargs))

        super(Sparse, self).__init__(
            mesh=mesh, objfcts=objfcts,
            alpha_s=alpha_s, alpha_x=alpha_x, alpha_y=alpha_y, alpha_z=alpha_z,
            **kwargs
        )

        # Utils.setKwargs(self, **kwargs)

    # Properties
    norms = properties.Array(
        "Norms used to create the sparse regularization",
        default=[0., 2., 2., 2.]
    )

    eps_p = properties.Float(
        "Threshold value for the model norm", default=1e-1
        )

    eps_q = properties.Float(
        "Threshold value for the model gradient norm", default=1e-1
        )

    model = properties.Array("current model", dtype=float)

    gamma = properties.Float(
        "Model norm scaling to smooth out convergence", default=1.
    )

    # Observers
    @properties.observer('norms')
    def _mirror_norms_to_objfcts(self, change):
        for i, objfct in enumerate(self.objfcts):
            objfct.norm = change['value'][i]

    @properties.observer('model')
    def _mirror_model_to_objfcts(self, change):
        for objfct in self.objfcts:
            objfct.model = change['value']

    @properties.observer('gamma')
    def _mirror_gamma_to_objfcts(self, change):
        for objfct in self.objfcts:
            objfct.gamma = change['value']

    @properties.observer('eps_p')
    def _mirror_eps_p_to_smallness(self, change):
        for objfct in self.objfcts:
            if isinstance(objfct, SparseSmallness):
                objfct.epsilon = change['value']

    @properties.observer('eps_q')
    def _mirror_eps_q_to_derivs(self, change):
        for objfct in self.objfcts:
            if isinstance(objfct, BaseSparseDeriv):
                objfct.epsilon = change['value']

# class Sparse(Simple):
#     """
#         The regularization is:

#         .. math::

#             R(m) = \\frac{1}{2}\mathbf{(m-m_\\text{ref})^\\top W^\\top R^\\top R W(m-m_\\text{ref})}

#         where the IRLS weight

#         .. math::

#             R = \eta TO FINISH LATER!!!

#         So the derivative is straight forward:
#         .. math::
#             R(m) = \mathbf{W^\\top R^\\top R W (m-m_\\text{ref})}

#         The IRLS weights are recomputed after each beta solves.
#         It is strongly recommended to do a few Gauss-Newton iterations
#         before updating.
#     """

#     # set default values
#     eps_p = 1e-1        # Threshold value for the model norm
#     eps_q = 1e-1        # Threshold value for the model gradient norm
#     model = None     # Requires model to compute the weights
#     l2model = None
#     gamma = 1.          # Model norm scaling to smooth out convergence
#     norms = [0., 2., 2., 2.] # Values for norm on (m, dmdx, dmdy, dmdz)
#     cell_weights = 1.        # Consider overwriting with sensitivity weights
#     def __init__(self, mesh, mapping=None, indActive=None, **kwargs):
#         Simple.__init__(self, mesh, mapping=mapping, indActive=indActive, **kwargs)
#         if isinstance(self.cell_weights,float):
#             self.cell_weights = np.ones(self.regmesh.nC) * self.cell_weights
#     @property
#     def Wsmall(self):
#         """Regularization matrix Wsmall"""
#         if getattr(self,'_Wsmall', None) is None:
#             if getattr(self, 'model', None) is None:
#                 self.Rs = Utils.speye(self.regmesh.nC)

#             else:
#                 f_m = self.mapping * (self.model - self.reg.mref)
#                 self.rs = self.R(f_m , self.eps_p, self.norms[0])
#                 self.Rs = Utils.sdiag( self.rs )

#             self._Wsmall = Utils.sdiag((self.alpha_s*self.gamma*self.cell_weights)**0.5)*self.Rs

#         return self._Wsmall

#     @property
#     def Wx(self):
#         """Regularization matrix Wx"""
#         if getattr(self,'_Wx', None) is None:
#             if getattr(self, 'model', None) is None:
#                 self.Rx = Utils.speye(self.regmesh.cellDiffxStencil.shape[0])

#             else:
#                 f_m = self.regmesh.cellDiffxStencil * (self.mapping * self.model)
#                 self.rx = self.R( f_m , self.eps_q, self.norms[1])
#                 self.Rx = Utils.sdiag( self.rx )

#             self._Wx = Utils.sdiag(( self.alpha_x*self.gamma*(self.regmesh.aveCC2Fx*self.cell_weights))**0.5)*self.Rx*self.regmesh.cellDiffxStencil

#         return self._Wx

#     @property
#     def Wy(self):
#         """Regularization matrix Wy"""
#         if getattr(self,'_Wy', None) is None:
#             if getattr(self, 'model', None) is None:
#                 self.Ry = Utils.speye(self.regmesh.cellDiffyStencil.shape[0])

#             else:
#                 f_m = self.regmesh.cellDiffyStencil * (self.mapping * self.model)
#                 self.ry = self.R( f_m , self.eps_q, self.norms[2])
#                 self.Ry = Utils.sdiag( self.ry )

#             self._Wy = Utils.sdiag((self.alpha_y*self.gamma*(self.regmesh.aveCC2Fy*self.cell_weights))**0.5)*self.Ry*self.regmesh.cellDiffyStencil

#         return self._Wy

#     @property
#     def Wz(self):
#         """Regularization matrix Wz"""
#         if getattr(self,'_Wz', None) is None:
#             if getattr(self, 'model', None) is None:
#                 self.Rz = Utils.speye(self.regmesh.cellDiffzStencil.shape[0])

#             else:
#                 f_m = self.regmesh.cellDiffzStencil * (self.mapping * self.model)
#                 self.rz = self.R( f_m , self.eps_q, self.norms[3])
#                 self.Rz = Utils.sdiag( self.rz )

#             self._Wz = Utils.sdiag((self.alpha_z*self.gamma*(self.regmesh.aveCC2Fz*self.cell_weights))**0.5)*self.Rz*self.regmesh.cellDiffzStencil

#         return self._Wz

#     def R(self, f_m , eps, exponent):

#         # Eta scaling is important for mix-norms...do not mess with it
#         eta = (eps**(1.-exponent/2.))**0.5
#         r = eta / (f_m**2.+ eps**2.)**((1.-exponent/2.)/2.)

#         return r
